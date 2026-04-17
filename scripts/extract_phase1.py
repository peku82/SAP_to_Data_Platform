"""extract_phase1.py

FASE 1 — Extracción inicial de SAP Business One a CSV.

Lee config/tables.yaml, itera sobre todas las tablas listadas, las extrae
usando el backend configurado en SAP_MODE y escribe a data/raw/<TABLA>_<YYYYMMDD>.csv

Uso:
    python scripts/extract_phase1.py
    python scripts/extract_phase1.py --tables OITM,OCRD
    python scripts/extract_phase1.py --since 2024-01-01
    python scripts/extract_phase1.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import yaml
except ImportError:
    print("Falta dependencia: pip install PyYAML", file=sys.stderr)
    sys.exit(2)

from sap_connection import get_connection  # noqa: E402

RAW_DIR = ROOT / "data" / "raw"
LOGS_DIR = ROOT / "logs"
CONFIG = ROOT / "config" / "tables.yaml"


def _setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    log_path = LOGS_DIR / f"extract_{today}.log"
    logger = logging.getLogger("extract_phase1")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def _load_tables() -> dict:
    with open(CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _flatten(tables_yaml: dict) -> list[tuple[str, str, dict]]:
    """Devuelve (group, table, spec) en orden."""
    out = []
    for group, tables in tables_yaml.items():
        for name, spec in tables.items():
            out.append((group, name, spec))
    return out


def _write_csv(path: Path, rows_iter, logger: logging.Logger,
               dry_run: bool = False) -> tuple[int, list[str]]:
    """Escribe CSV y devuelve (count, columns)."""
    count = 0
    columns: list[str] = []
    tmp = path.with_suffix(".csv.part")
    path.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        for row in rows_iter:
            if not columns:
                columns = list(row.keys())
            count += 1
            if count % 5000 == 0:
                logger.info(f"  dry-run leídas {count} filas")
        return count, columns

    writer: Optional[csv.DictWriter] = None
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        for row in rows_iter:
            if writer is None:
                columns = list(row.keys())
                writer = csv.DictWriter(
                    f,
                    fieldnames=columns,
                    quoting=csv.QUOTE_ALL,
                    lineterminator="\n",
                )
                writer.writeheader()
            # Normalizar valores no serializables a string
            safe = {
                k: ("" if v is None else v if isinstance(v, (str, int, float)) else str(v))
                for k, v in row.items()
            }
            writer.writerow(safe)
            count += 1
            if count % 5000 == 0:
                logger.info(f"  escritas {count} filas")

    if count == 0:
        tmp.touch()
    tmp.replace(path)
    return count, columns


def run(tables_filter: Optional[list[str]], since_override: Optional[str],
        dry_run: bool, logger: logging.Logger) -> dict:
    today = dt.date.today().strftime("%Y%m%d")
    tables_yaml = _load_tables()
    flat = _flatten(tables_yaml)
    if tables_filter:
        flat = [t for t in flat if t[1] in tables_filter]
        if not flat:
            raise SystemExit(f"No hay tablas que coincidan con {tables_filter}")

    since_default = since_override or os.environ.get("EXTRACT_SINCE")
    report: dict = {
        "started_at": dt.datetime.now().isoformat(timespec="seconds"),
        "mode": None,
        "dry_run": dry_run,
        "tables": {},
        "totals": {"rows": 0, "tables_ok": 0, "tables_failed": 0},
    }

    t_start = time.time()
    with get_connection() as conn:
        report["mode"] = conn.mode
        logger.info(f"Conectado a SAP — modo: {conn.mode}")
        for group, table, spec in flat:
            logger.info(f"[{group}] {table} — extrayendo…")
            since_col = spec.get("since_col")
            since = since_default if since_col else None
            out_path = RAW_DIR / f"{table}_{today}.csv"
            t0 = time.time()
            try:
                total_expected = None
                try:
                    total_expected = conn.count_table(table)
                except Exception as e:
                    logger.warning(f"  count_table falló para {table}: {e}")
                rows = conn.fetch_table(table, since=since, since_col=since_col)
                count, columns = _write_csv(out_path, rows, logger, dry_run=dry_run)
                dur = time.time() - t0
                logger.info(
                    f"  {table}: {count} filas escritas en {dur:.1f}s"
                    + (f" (SAP dice {total_expected})" if total_expected is not None else "")
                )
                report["tables"][table] = {
                    "group": group,
                    "rows_written": count,
                    "rows_reported_by_sap": total_expected,
                    "columns": columns,
                    "since_col": since_col,
                    "since_value": since,
                    "path": str(out_path) if not dry_run else None,
                    "duration_sec": round(dur, 2),
                    "status": "ok",
                }
                report["totals"]["rows"] += count
                report["totals"]["tables_ok"] += 1
            except Exception as e:
                logger.exception(f"  {table}: FALLÓ — {e}")
                report["tables"][table] = {
                    "group": group,
                    "status": "error",
                    "error": str(e),
                }
                report["totals"]["tables_failed"] += 1

    report["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")
    report["duration_sec"] = round(time.time() - t_start, 2)

    report_path = LOGS_DIR / f"extract_{today}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"Reporte: {report_path}")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Fase 1 — extracción SAP → CSV")
    ap.add_argument("--tables", help="Lista de tablas separadas por coma")
    ap.add_argument("--since", help="Fecha ISO para filtro inicial (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true",
                    help="No escribe CSV, solo cuenta filas")
    args = ap.parse_args()

    logger = _setup_logging()
    logger.info("=" * 60)
    logger.info("FASE 1 — extracción SAP B1")
    logger.info("=" * 60)

    tables_filter = args.tables.split(",") if args.tables else None

    try:
        report = run(tables_filter, args.since, args.dry_run, logger)
    except Exception as e:
        logger.exception(f"Error fatal: {e}")
        return 1

    logger.info(
        f"Fin. OK={report['totals']['tables_ok']} "
        f"FAIL={report['totals']['tables_failed']} "
        f"filas={report['totals']['rows']}"
    )
    return 0 if report["totals"]["tables_failed"] == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
