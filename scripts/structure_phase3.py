"""
Fase 3 — Estructura.

Valida integridad referencial (FKs implicitas) entre las tablas de data/clean/.
Reporta:
  - cantidad de filas hijas con FK que NO existe en la tabla padre (huerfanos),
  - sample (primeros 5 keys huerfanos) para investigacion.

NO altera la data; solo reporta. La data huerfana suele ser real en SAP B1 y
hay que decidir caso por caso si:
  (a) se ignora (soft FK, comun en CardCode borrado pero referenciado en historicos),
  (b) se importa con FK NULL en PG (relajando la constraint), o
  (c) se invalida la fila al cargar.

Salida:
  - logs/structure_<fecha>.json
  - logs/structure_<fecha>.log
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
LOGS = ROOT / "logs"
DATE_TAG = "20260429"


# (child_table, child_fk_cols)  ->  (parent_table, parent_pk_cols)
# Solo FKs core que importan para el modelo Odoo.
FK_RULES = [
    # Maestros
    ("OITM", ["items_grp_cod"], "OITB", ["itms_grp_cod"]),
    ("ITM1",  ["item_code"],     "OITM", ["item_code"]),
    # Inventario
    ("OITW", ["item_code"], "OITM", ["item_code"]),
    ("OBTN", ["item_code"], "OITM", ["item_code"]),
    ("OBTQ", ["item_code"], "OITM", ["item_code"]),
    ("OBTQ", ["item_code", "sys_number"], "OBTN", ["item_code", "sys_number"]),
    # Operaciones - ventas
    ("ORDR", ["card_code"], "OCRD", ["card_code"]),
    ("RDR1", ["doc_entry"], "ORDR", ["doc_entry"]),
    ("RDR1", ["item_code"], "OITM", ["item_code"]),
    # Operaciones - compras
    ("OPOR", ["card_code"], "OCRD", ["card_code"]),
    ("POR1", ["doc_entry"], "OPOR", ["doc_entry"]),
    ("POR1", ["item_code"], "OITM", ["item_code"]),
    # Historico - facturas venta
    ("OINV", ["card_code"], "OCRD", ["card_code"]),
    ("INV1", ["doc_entry"], "OINV", ["doc_entry"]),
    ("INV1", ["item_code"], "OITM", ["item_code"]),
    # Historico - facturas compra
    ("OPCH", ["card_code"], "OCRD", ["card_code"]),
    ("PCH1", ["doc_entry"], "OPCH", ["doc_entry"]),
    ("PCH1", ["item_code"], "OITM", ["item_code"]),
    # Contabilidad
    ("JDT1", ["trans_id"],  "OJDT", ["trans_id"]),
    ("JDT1", ["acct_code"], "OACT", ["acct_code"]),
]


def _setup_logging() -> logging.Logger:
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"structure_{DATE_TAG}.log"
    logger = logging.getLogger("structure")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s")
    for h in (logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()):
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger


def _load(table: str, cols: list[str]) -> pl.DataFrame:
    path = CLEAN / f"{table}_{DATE_TAG}.csv"
    return pl.read_csv(path, infer_schema_length=0, columns=cols)


def check_fk(child: str, child_cols: list[str], parent: str, parent_cols: list[str]) -> dict:
    df_child = _load(child, child_cols)
    df_parent = _load(parent, parent_cols).rename(
        {pc: cc for pc, cc in zip(parent_cols, child_cols)}
    )

    # Filas hijas con cualquier FK no nulo
    keep_filter = pl.lit(True)
    for c in child_cols:
        keep_filter = keep_filter & pl.col(c).is_not_null() & (pl.col(c) != "")
    df_child_nonnull = df_child.filter(keep_filter)
    n_child = df_child.height
    n_child_with_fk = df_child_nonnull.height

    # Anti-join: filas hijas cuyo FK no esta en parent
    df_orphans = df_child_nonnull.join(df_parent, on=child_cols, how="anti")
    n_orphans = df_orphans.height

    sample = []
    if n_orphans > 0:
        for row in df_orphans.head(5).to_dicts():
            sample.append({k: row[k] for k in child_cols})

    # Tambien contar nulls/empties en FK
    n_null_fk = n_child - n_child_with_fk

    return {
        "child": child,
        "child_cols": child_cols,
        "parent": parent,
        "parent_cols": parent_cols,
        "child_rows": n_child,
        "child_rows_with_fk": n_child_with_fk,
        "child_rows_with_null_fk": n_null_fk,
        "orphans": n_orphans,
        "orphan_pct": round(100 * n_orphans / n_child_with_fk, 3) if n_child_with_fk else 0,
        "sample": sample,
    }


def main() -> int:
    logger = _setup_logging()
    logger.info(f"Fase 3 - structure (FK checks) sobre data/clean/{DATE_TAG}")
    results = []
    total_orphans = 0
    for child, child_cols, parent, parent_cols in FK_RULES:
        try:
            r = check_fk(child, child_cols, parent, parent_cols)
        except Exception as e:
            r = {
                "child": child,
                "child_cols": child_cols,
                "parent": parent,
                "parent_cols": parent_cols,
                "error": str(e),
            }
            logger.error(f"FAIL {child}->{parent}: {e}")
            results.append(r)
            continue

        results.append(r)
        total_orphans += r["orphans"]
        marker = "OK " if r["orphans"] == 0 else "WARN"
        logger.info(
            f"  {marker}  {child}.{','.join(child_cols)} -> {parent}.{','.join(parent_cols)}  "
            f"child_rows={r['child_rows']:>10,}  null_fk={r['child_rows_with_null_fk']:>8,}  "
            f"orphans={r['orphans']:>8,}  ({r['orphan_pct']}%)"
        )

    out = {
        "phase": "3_structure",
        "date_tag": DATE_TAG,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "fk_rules_count": len(FK_RULES),
        "total_orphans": total_orphans,
        "results": results,
    }
    out_path = LOGS / f"structure_{DATE_TAG}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    logger.info(f"\nReporte: {out_path}")
    logger.info(f"Total huerfanos: {total_orphans:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
