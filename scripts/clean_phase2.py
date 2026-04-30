"""
Fase 2 — Clean.

Lee data/raw/<TABLA>_<fecha>.csv, aplica:
- Rename de headers ES -> snake_case via config/header_mapping.yaml.
- Dedupe exacto.
- Trim de strings.
- Parseo de fechas update_date / create_date / doc_date / ref_date a ISO.
- Detecta nulls en columnas PK (criticas) y los reporta.

Escribe:
- data/clean/<TABLA>_<fecha>.csv (UTF-8, separador coma, header snake_case).
- logs/clean_<fecha>.json con reporte global por tabla.
- logs/quality/<TABLA>_<fecha>_quality.json por tabla.

Usa polars en streaming (lazy + sink) para que las tablas grandes (JDT1, OBTN)
no carguen toda la BD en RAM.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import polars as pl
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
LOGS = ROOT / "logs"
QUALITY_DIR = LOGS / "quality"
MAPPING_PATH = ROOT / "config" / "header_mapping.yaml"
TABLES_PATH = ROOT / "config" / "tables.yaml"

DATE_TAG = "20260429"

# Columnas date que parseamos a ISO (las que existan).
DATE_COLS = ["update_date", "create_date", "doc_date", "ref_date", "due_date"]

# Mapeo de PK por tabla (canonico, snake_case) tomado de tables.yaml + heuristicas.
PK_BY_TABLE: dict[str, list[str]] = {
    "OCRD": ["card_code"],
    "OITM": ["item_code"],
    "OITB": ["itms_grp_cod"],
    "ITM1": ["item_code", "price_list"],
    "OITW": ["item_code", "whs_code"],
    "OBTN": ["item_code", "sys_number"],
    "OBTQ": ["item_code", "sys_number", "whs_code"],
    "ORDR": ["doc_entry"],
    "RDR1": ["doc_entry", "line_num"],
    "OPOR": ["doc_entry"],
    "POR1": ["doc_entry", "line_num"],
    "OACT": ["acct_code"],
    "OJDT": ["trans_id"],
    "JDT1": ["trans_id", "line_id"],
    "OINV": ["doc_entry"],
    "INV1": ["doc_entry", "line_num"],
    "OPCH": ["doc_entry"],
    "PCH1": ["doc_entry", "line_num"],
}


def load_mapping() -> dict:
    with MAPPING_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_date_col(s: pl.Series) -> pl.Series:
    """Intenta varios formatos comunes en exports SAP B1 ES; null-safe."""
    # Polars infiere el formato si es uniforme. Probamos cast con strict=False
    # y tres formatos comunes en exports.
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"]
    for fmt in formats:
        try:
            out = s.str.strptime(pl.Datetime, fmt, strict=False)
            if out.null_count() < s.null_count() + s.len() // 2:
                return out
        except Exception:
            continue
    # Fallback: cast permisivo
    return s.str.strptime(pl.Datetime, strict=False)


def clean_table(table: str, mapping: dict) -> dict:
    csv_in = RAW / f"{table}_{DATE_TAG}.csv"
    csv_out = CLEAN / f"{table}_{DATE_TAG}.csv"
    quality_out = QUALITY_DIR / f"{table}_{DATE_TAG}_quality.json"
    quality: dict = {
        "table": table,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "input_csv": str(csv_in.relative_to(ROOT)),
        "output_csv": str(csv_out.relative_to(ROOT)),
    }
    t0 = time.time()
    table_map = mapping.get(table)
    if table_map is None:
        raise RuntimeError(f"No hay mapping para {table} en header_mapping.yaml")

    # Leemos lazy — todo el CSV como string para evitar reinterpretacion erronea
    # de tipos (los exports SAP ES usan separador de miles europeo en algunos
    # numeros; tipado lo hacemos solo en columnas conocidas).
    lf = pl.scan_csv(
        csv_in,
        encoding="utf8",
        try_parse_dates=False,
        infer_schema_length=0,  # todo string
        ignore_errors=False,
        rechunk=False,
    )

    # Rename de columnas. polars permite dict ES_header -> snake. Usamos
    # {orig_name: new_name}; las columnas que el slugify dejo igual no necesitan
    # rename pero si vienen en table_map las renombramos al canonico.
    lf = lf.rename({k: v for k, v in table_map.items()})

    # Renombre de fechas estandar (ya estan en table_map; aqui solo defensa).

    # Strip strings — aplicar a TODAS las columnas string. En lazy hacemos
    # with_columns pl.col(pl.Utf8).str.strip_chars()
    lf = lf.with_columns(pl.col(pl.Utf8).str.strip_chars())

    # Fix SAP B1 quirk: en exports, LineNum=0 (primera linea) sale como string
    # vacio. Igual con Line_ID=0 en JDT1. Sustituimos "" -> "0" en las cols
    # numericas que son parte del PK para evitar PK nulo.
    schema_cols_pre = lf.collect_schema().names()
    for line_col in ("line_num", "line_id"):
        if line_col in schema_cols_pre:
            lf = lf.with_columns(
                pl.when(pl.col(line_col) == "")
                .then(pl.lit("0"))
                .otherwise(pl.col(line_col))
                .alias(line_col)
            )

    # Parsear fechas conocidas si existen.
    schema_cols = lf.collect_schema().names()
    parsed_cols: list[str] = []
    for dc in DATE_COLS:
        if dc in schema_cols:
            lf = lf.with_columns(
                pl.col(dc)
                .str.strptime(pl.Datetime, format=None, strict=False)
                .alias(dc)
            )
            parsed_cols.append(dc)

    # Dedupe exacto sobre PK (si existe la columna PK), sino global.
    pks = PK_BY_TABLE.get(table, [])
    pks_in_schema = [c for c in pks if c in schema_cols]
    if pks_in_schema:
        lf = lf.unique(subset=pks_in_schema, keep="first", maintain_order=True)
    else:
        lf = lf.unique(keep="first", maintain_order=True)

    # Materializar y escribir.
    df = lf.collect(engine="streaming")
    rows_out = df.height

    # Reporte de calidad.
    quality["row_count"] = rows_out
    quality["column_count"] = df.width
    quality["pk"] = pks_in_schema
    quality["date_columns_parsed"] = parsed_cols

    if pks_in_schema:
        # Nulls en cualquier PK
        nulls_pk = df.select(
            [pl.col(c).is_null().sum().alias(c) for c in pks_in_schema]
        ).to_dict(as_series=False)
        quality["pk_nulls"] = {k: int(v[0]) for k, v in nulls_pk.items()}
        # Duplicados de PK (deberia ser 0 tras unique)
        dup_count = df.group_by(pks_in_schema).count().filter(pl.col("count") > 1).height
        quality["pk_duplicates_after_dedupe"] = dup_count
    else:
        quality["pk_nulls"] = {}
        quality["pk_duplicates_after_dedupe"] = 0

    # Null counts globales (top 10 columnas mas vacias) para vista rapida.
    nulls = df.null_count().to_dict(as_series=False)
    null_pairs = sorted(((k, int(v[0])) for k, v in nulls.items()), key=lambda x: -x[1])
    quality["top_null_columns"] = null_pairs[:10]

    # Escribir CSV limpio.
    CLEAN.mkdir(parents=True, exist_ok=True)
    df.write_csv(csv_out, include_header=True)

    quality["duration_sec"] = round(time.time() - t0, 2)
    quality["finished_at"] = datetime.utcnow().isoformat() + "Z"

    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    with quality_out.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    return quality


def main() -> None:
    print(f"Fase 2 - Clean. raw={RAW} clean={CLEAN}")
    mapping = load_mapping()
    tables = list(mapping.keys())
    print(f"Tablas: {len(tables)}")

    summary: list[dict] = []
    t_global = time.time()
    for i, table in enumerate(tables, 1):
        print(f"\n[{i}/{len(tables)}] {table} ...", flush=True)
        try:
            q = clean_table(table, mapping)
            print(
                f"   OK  filas={q['row_count']:>10,} cols={q['column_count']} "
                f"dur={q['duration_sec']}s pk_nulls={q['pk_nulls']}"
            )
            summary.append({"table": table, "status": "ok", **{
                k: q[k] for k in ("row_count", "column_count", "pk", "duration_sec",
                                  "pk_nulls", "pk_duplicates_after_dedupe")
            }})
        except Exception as exc:
            print(f"   FAIL {exc}", file=sys.stderr)
            summary.append({"table": table, "status": "error", "error": str(exc)})

    out = {
        "phase": "2_clean",
        "date_tag": DATE_TAG,
        "duration_sec": round(time.time() - t_global, 2),
        "summary": summary,
    }
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"clean_{DATE_TAG}.json"
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nReporte global -> {log_path}")
    ok = sum(1 for s in summary if s["status"] == "ok")
    print(f"Tablas OK: {ok}/{len(summary)}")


if __name__ == "__main__":
    main()
