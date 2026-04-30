"""
Fase 4 — Carga a PostgreSQL.

1. Crea el schema 'sap' y dropea+recrea las 18 tablas.
2. Carga cada CSV de data/clean/ con COPY FROM STDIN (rapido).
3. Crea PRIMARY KEY constraint sobre los PKs canonicos.
4. Crea indices sobre columnas watermark (update_date) para deltas.
5. Verifica conteos PG vs expected_counts.yaml.

NO crea FOREIGN KEYS porque hay 332 huerfanos historicos en SAP B1
(reportados por structure_phase3.py). Soft-FK: la integridad se valida
al transformar a Odoo, no al cargar.

Variables de entorno:
  PG_DSN  postgresql://user:pass@host:port/db
          (default: postgresql:///sap_replica via socket local)
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2
import yaml

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
LOGS = ROOT / "logs"
DATE_TAG = "20260429"

EXPECTED = ROOT / "config" / "expected_counts.yaml"
TABLES_YAML = ROOT / "config" / "tables.yaml"
HEADER_MAPPING = ROOT / "config" / "header_mapping.yaml"

DSN = os.environ.get("PG_DSN", "postgresql:///sap_replica")

# Columnas que se castean a TIMESTAMP en PG (vienen como ISO de Polars).
TIMESTAMP_COLS = {"update_date", "create_date", "doc_date", "ref_date", "due_date"}

# Mapeo PK SAP -> snake (mismo que validate_extraction.py).
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


def normalize_pk(pk) -> list[str]:
    if isinstance(pk, str):
        pk = [pk]
    return [PK_SAP_TO_SNAKE.get(c, c.lower()) for c in pk]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_pk_map() -> dict[str, list[str]]:
    """De tables.yaml -> {TABLE: [pk_snake_cols]}."""
    out: dict[str, list[str]] = {}
    spec = load_yaml(TABLES_YAML)
    for group, tables in spec.items():
        for t, s in tables.items():
            out[t] = normalize_pk(s.get("pk"))
    return out


def csv_columns(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        return next(csv.reader(f))


def quote_ident(name: str) -> str:
    """Quota identificador PG si tiene caracteres dudosos."""
    safe = all(c.isalnum() or c == "_" for c in name) and name[:1].isalpha()
    return name if safe else '"' + name.replace('"', '""') + '"'


def build_ddl(table: str, columns: list[str], pk_cols: list[str]) -> str:
    pg_table = table.lower()
    coldefs = []
    seen = set()
    for c in columns:
        c_pg = c
        # Si hay duplicados (no deberia haber tras disambiguate), agregar sufijo
        if c_pg in seen:
            i = 2
            while f"{c_pg}_{i}" in seen:
                i += 1
            c_pg = f"{c_pg}_{i}"
        seen.add(c_pg)
        if c_pg in TIMESTAMP_COLS:
            coldefs.append(f"  {quote_ident(c_pg)} TIMESTAMP")
        else:
            coldefs.append(f"  {quote_ident(c_pg)} TEXT")
    pk_cols_present = [c for c in pk_cols if c in seen]
    if pk_cols_present:
        pk = ", ".join(quote_ident(c) for c in pk_cols_present)
        coldefs.append(f"  CONSTRAINT pk_{pg_table} PRIMARY KEY ({pk})")
    body = ",\n".join(coldefs)
    return f"DROP TABLE IF EXISTS sap.{pg_table};\nCREATE TABLE sap.{pg_table} (\n{body}\n);"


def index_ddl(table: str, columns: list[str]) -> list[str]:
    pg_table = table.lower()
    out = []
    for c in ("update_date", "create_date", "doc_date", "ref_date"):
        if c in columns:
            out.append(
                f"CREATE INDEX IF NOT EXISTS idx_{pg_table}_{c} "
                f"ON sap.{pg_table} ({quote_ident(c)});"
            )
    return out


def load_table(conn, table: str, csv_path: Path, columns: list[str], pk_cols: list[str]) -> dict:
    pg_table = table.lower()
    t0 = time.time()

    # 1. DDL
    ddl = build_ddl(table, columns, pk_cols)
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()

    # 2. COPY
    # Usamos STDIN con CSV HEADER. Para columnas TIMESTAMP, polars escribe ISO
    # ("2024-01-15T10:30:00.000000") que PG acepta. Empty string es NULL.
    cols_quoted = ", ".join(quote_ident(c) for c in columns)
    copy_sql = (
        f"COPY sap.{pg_table} ({cols_quoted}) "
        f"FROM STDIN WITH (FORMAT csv, HEADER true, "
        f"NULL '', QUOTE '\"', ESCAPE '\"', DELIMITER ',')"
    )
    with conn.cursor() as cur, csv_path.open("r", encoding="utf-8") as f:
        cur.copy_expert(copy_sql, f)
    conn.commit()

    # 3. Indices (date watermarks)
    with conn.cursor() as cur:
        for stmt in index_ddl(table, columns):
            cur.execute(stmt)
        # Conteo
        cur.execute(f"SELECT COUNT(*) FROM sap.{pg_table}")
        rows = cur.fetchone()[0]
    conn.commit()

    return {"table": table, "pg_table": pg_table, "rows": rows, "duration_sec": round(time.time() - t0, 2)}


def main() -> int:
    print(f"Fase 4 - Carga PostgreSQL  DSN={DSN}")
    expected = load_yaml(EXPECTED) or {}
    pk_map = get_pk_map()
    tables = list(pk_map.keys())

    conn = psycopg2.connect(DSN)
    conn.autocommit = False

    # Schema
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS sap;")
    conn.commit()

    summary = []
    t_global = time.time()
    for i, table in enumerate(tables, 1):
        csv_path = CLEAN / f"{table}_{DATE_TAG}.csv"
        if not csv_path.exists():
            print(f"[{i}/{len(tables)}] {table}: SKIP (no CSV)")
            summary.append({"table": table, "status": "skipped"})
            continue
        cols = csv_columns(csv_path)
        pk_cols = pk_map[table]
        try:
            r = load_table(conn, table, csv_path, cols, pk_cols)
        except Exception as exc:
            conn.rollback()
            print(f"[{i}/{len(tables)}] {table}: FAIL {exc}", file=sys.stderr)
            summary.append({"table": table, "status": "error", "error": str(exc)})
            continue
        exp = expected.get(table)
        diff = (r["rows"] - exp) if exp is not None else None
        ok = (diff == 0) if diff is not None else True
        summary.append({**r, "expected": exp, "diff": diff, "status": "ok" if ok else "diff"})
        print(
            f"[{i:>2}/{len(tables)}] {table:6s} -> sap.{r['pg_table']:6s} "
            f"rows={r['rows']:>10,} exp={exp if exp else 'NA':>10} diff={diff} "
            f"dur={r['duration_sec']}s"
        )

    # Reporte
    out = {
        "phase": "4_load",
        "date_tag": DATE_TAG,
        "dsn": DSN if "@" not in DSN else DSN.split("@")[1],  # sin password
        "duration_sec": round(time.time() - t_global, 2),
        "summary": summary,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = LOGS / f"load_{DATE_TAG}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    ok = sum(1 for s in summary if s.get("status") == "ok")
    print(f"\nReporte: {out_path}\nTablas OK: {ok}/{len(summary)}  total dur={out['duration_sec']}s")

    conn.close()
    return 0 if ok == len(summary) else 4


if __name__ == "__main__":
    sys.exit(main())
