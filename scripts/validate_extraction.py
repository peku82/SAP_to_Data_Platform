"""validate_extraction.py

Valida la extraccion + clean (Fase 1 + Fase 2).

Compara cada CSV de data/clean/ contra los conteos confirmados que reporto SAP
en la Fase 1 y detecta:

  - faltantes (CSV no existe)
  - diferencias de conteo
  - PKs duplicados (en snake_case canonico)
  - PKs con valor nulo

Esta version YA NO necesita conexion live a SAP. Los conteos confirmados se
leen desde config/expected_counts.yaml (snapshot 2026-04-29 hecho por Victor).
Para la siguiente carga delta, se actualiza ese YAML o se enchufa de nuevo
la conexion SAP via --use-sap.

Uso:
    python scripts/validate_extraction.py
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

CLEAN_DIR = ROOT / "data" / "clean"
LOGS_DIR = ROOT / "logs"
TABLES_CONFIG = ROOT / "config" / "tables.yaml"
EXPECTED_CONFIG = ROOT / "config" / "expected_counts.yaml"
MAPPING_CONFIG = ROOT / "config" / "header_mapping.yaml"


def _setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    log_path = LOGS_DIR / f"validate_{today}.log"
    logger = logging.getLogger("validate")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s")
    for h in (
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ):
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger


def _latest_clean_csv(table: str) -> Path | None:
    matches = sorted(CLEAN_DIR.glob(f"{table}_*.csv"))
    return matches[-1] if matches else None


# Mapeo PK ES -> snake usado por la version original (ya no es necesario porque
# data/clean/ usa snake_case directo, pero lo dejamos como fallback por si
# alguien apunta el validador a data/raw/).
PK_SAP_TO_SNAKE = {
    "CardCode": "card_code",
    "ItemCode": "item_code",
    "ItmsGrpCod": "itms_grp_cod",
    "PriceList": "price_list",
    "WhsCode": "whs_code",
    "SysNumber": "sys_number",
    "DocEntry": "doc_entry",
    "LineNum": "line_num",
    "AcctCode": "acct_code",
    "TransId": "trans_id",
    "Line_ID": "line_id",
}


def _normalize_pk(pk) -> list[str]:
    """tables.yaml define PKs en CamelCase SAP. Mapeamos a snake_case."""
    if isinstance(pk, str):
        pk = [pk]
    out = []
    for c in pk:
        out.append(PK_SAP_TO_SNAKE.get(c, c.lower()))
    return out


def _scan_csv(path: Path, pk_cols: list[str]) -> dict:
    """Recorre el CSV una sola vez, devuelve filas, dup PKs, nulls PKs, columnas."""
    seen: set[tuple] = set()
    dups = 0
    nulls = {c: 0 for c in pk_cols}
    count = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        missing_pks = [c for c in pk_cols if c not in cols]
        for row in reader:
            count += 1
            key_vals = []
            for c in pk_cols:
                v = (row.get(c) or "").strip()
                if not v:
                    nulls[c] = nulls.get(c, 0) + 1
                key_vals.append(v)
            key = tuple(key_vals)
            if key in seen:
                dups += 1
            else:
                seen.add(key)
    return {
        "count": count,
        "dups": dups,
        "nulls": nulls,
        "columns": cols,
        "missing_pks": missing_pks,
    }


def main() -> int:
    logger = _setup_logging()
    with TABLES_CONFIG.open("r", encoding="utf-8") as f:
        tables_yaml = yaml.safe_load(f)

    if EXPECTED_CONFIG.exists():
        with EXPECTED_CONFIG.open("r", encoding="utf-8") as f:
            expected = yaml.safe_load(f) or {}
    else:
        logger.warning(
            f"{EXPECTED_CONFIG.name} no existe — corriendo sin validar conteo SAP."
        )
        expected = {}

    results: list[dict] = []
    errors = 0

    logger.info(f"Validacion vs. data/clean/ + expected_counts.yaml")
    for group, tables in tables_yaml.items():
        for table, spec in tables.items():
            csv_path = _latest_clean_csv(table)
            pk_snake = _normalize_pk(spec.get("pk"))
            entry = {
                "group": group,
                "table": table,
                "csv": str(csv_path) if csv_path else None,
                "pk_snake": pk_snake,
                "status": "ok",
                "expected_count": expected.get(table),
                "csv_count": None,
                "diff": None,
                "pk_duplicates": 0,
                "pk_nulls": {},
                "issues": [],
            }
            if csv_path is None:
                entry["status"] = "missing_csv"
                entry["issues"].append("no existe CSV en data/clean/")
                errors += 1
                results.append(entry)
                continue

            scan = _scan_csv(csv_path, pk_snake)
            entry["csv_count"] = scan["count"]
            entry["pk_duplicates"] = scan["dups"]
            entry["pk_nulls"] = scan["nulls"]
            if scan["missing_pks"]:
                entry["status"] = "pk_missing_in_csv"
                entry["issues"].append(
                    f"PKs no encontrados como columnas: {scan['missing_pks']}"
                )
                errors += 1

            exp = entry["expected_count"]
            if exp is not None:
                entry["diff"] = scan["count"] - exp
                if entry["diff"] != 0:
                    entry["status"] = "count_mismatch"
                    entry["issues"].append(
                        f"CSV tiene {scan['count']} filas, SAP reporta {exp}"
                    )
                    errors += 1

            if scan["dups"]:
                entry["status"] = (
                    "pk_dup" if entry["status"] == "ok" else entry["status"]
                )
                entry["issues"].append(f"{scan['dups']} PKs duplicados")
                errors += 1

            null_total = sum(scan["nulls"].values())
            if null_total > 0:
                entry["status"] = (
                    "pk_null" if entry["status"] == "ok" else entry["status"]
                )
                entry["issues"].append(f"{null_total} valores nulos en PKs")
                errors += 1

            logger.info(
                f"[{group:13s}] {table:6s} csv={scan['count']:>10,} "
                f"sap={exp if exp is not None else 'NA':>10} "
                f"diff={entry['diff']} dups={scan['dups']} "
                f"nulls={null_total} -> {entry['status']}"
            )
            results.append(entry)

    today = dt.date.today().strftime("%Y%m%d")
    out = LOGS_DIR / f"validate_{today}.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                "results": results,
                "errors": errors,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info(f"Reporte: {out}")
    logger.info(f"Errores: {errors}")
    return 0 if errors == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
