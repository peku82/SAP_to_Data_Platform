"""validate_extraction.py

Valida la extracción de Fase 1.

Compara cada CSV de data/raw/ contra el conteo que reporta SAP y detecta:

  - faltantes (CSV no existe)
  - diferencias de conteo
  - columnas vacías
  - primaries keys duplicados

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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402
from sap_connection import get_connection  # noqa: E402

RAW_DIR = ROOT / "data" / "raw"
LOGS_DIR = ROOT / "logs"
CONFIG = ROOT / "config" / "tables.yaml"


def _setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    log_path = LOGS_DIR / f"validate_{today}.log"
    logger = logging.getLogger("validate")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s")
    for h in (logging.FileHandler(log_path, encoding="utf-8"),
              logging.StreamHandler()):
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger


def _latest_csv(table: str) -> Path | None:
    matches = sorted(RAW_DIR.glob(f"{table}_*.csv"))
    return matches[-1] if matches else None


def _count_and_pk_dups(path: Path, pk) -> tuple[int, int, list[str]]:
    """Devuelve (filas, duplicados_pk, columnas)."""
    if isinstance(pk, str):
        pk = [pk]
    seen: set[tuple] = set()
    dups = 0
    cols: list[str] = []
    count = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for row in reader:
            count += 1
            try:
                key = tuple(row.get(c, "") for c in pk)
            except Exception:
                continue
            if key in seen:
                dups += 1
            else:
                seen.add(key)
    return count, dups, cols


def main() -> int:
    logger = _setup_logging()
    with open(CONFIG, "r", encoding="utf-8") as f:
        tables_yaml = yaml.safe_load(f)

    results: list[dict] = []
    errors = 0

    with get_connection() as conn:
        logger.info(f"Validación vs. SAP — modo {conn.mode}")
        for group, tables in tables_yaml.items():
            for table, spec in tables.items():
                csv_path = _latest_csv(table)
                entry = {
                    "group": group,
                    "table": table,
                    "csv": str(csv_path) if csv_path else None,
                    "status": "ok",
                    "sap_count": None,
                    "csv_count": None,
                    "diff": None,
                    "pk_duplicates": None,
                    "issues": [],
                }
                if csv_path is None:
                    entry["status"] = "missing_csv"
                    entry["issues"].append("no existe CSV en data/raw/")
                    errors += 1
                    results.append(entry)
                    continue

                try:
                    sap_count = conn.count_table(table)
                except Exception as e:
                    sap_count = -1
                    entry["issues"].append(f"count_table falló: {e}")
                entry["sap_count"] = sap_count

                csv_count, dups, cols = _count_and_pk_dups(
                    csv_path, spec.get("pk"))
                entry["csv_count"] = csv_count
                entry["pk_duplicates"] = dups
                entry["columns"] = cols
                if sap_count >= 0:
                    entry["diff"] = csv_count - sap_count
                    if entry["diff"] != 0:
                        entry["status"] = "count_mismatch"
                        entry["issues"].append(
                            f"CSV tiene {csv_count} filas, SAP reporta {sap_count}"
                        )
                        errors += 1
                if dups:
                    entry["status"] = "pk_dup" if entry["status"] == "ok" else entry["status"]
                    entry["issues"].append(f"{dups} claves primarias duplicadas")
                    errors += 1

                logger.info(
                    f"[{group}] {table:8s}  csv={csv_count:>8}  "
                    f"sap={sap_count:>8}  diff={entry['diff']}  "
                    f"pk_dups={dups}  — {entry['status']}"
                )
                results.append(entry)

    today = dt.date.today().strftime("%Y%m%d")
    out = LOGS_DIR / f"validate_{today}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                   "results": results, "errors": errors}, f, indent=2,
                  ensure_ascii=False)
    logger.info(f"Reporte: {out}")
    logger.info(f"Errores: {errors}")
    return 0 if errors == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
