"""
Construye config/header_mapping.yaml a partir de los CSVs en data/raw/.

Estrategia:
- Lee la primera fila de cada CSV.
- Convierte cada header ES a snake_case ascii determinista.
- Override manual para los PKs canonicos de SAP (CardCode, ItemCode, DocEntry, ...)
  para que el validador y el schema coincidan con tables.yaml.

Salida: config/header_mapping.yaml con bloque por tabla:
  TABLA:
    "Header original ES": snake_case_name
    ...
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CONFIG = ROOT / "config" / "header_mapping.yaml"

TABLES = [
    "INV1", "ITM1", "JDT1", "OACT", "OBTN", "OBTQ", "OCRD",
    "OINV", "OITB", "OITM", "OITW", "OJDT", "OPCH", "OPOR",
    "ORDR", "PCH1", "POR1", "RDR1",
]

DATE_TAG = "20260429"

# Override exacto para los PKs y FKs canonicos que aparecen en tables.yaml.
# Llave = (TABLA, header_es_normalizado_lower). Valor = snake_case canonico.
# Aplicamos despues del slugify automatico para sobreescribir.
# Override estandar para todas las tablas que tengan estas fechas (watermarks deltas).
# Aplicado dinamicamente: si el slug coincide en cualquier tabla, se reemplaza.
DATE_OVERRIDES = {
    "fecha_de_actualizacion": "update_date",
    "fecha_de_creacion": "create_date",
    "fecha_de_actualizacion_historial": "update_date",
    "fecha_de_creacion_historial": "create_date",
}

PK_OVERRIDES = {
    # OCRD: CardCode, CardName
    ("OCRD", "codigo_sn"): "card_code",
    ("OCRD", "nombre_sn"): "card_name",
    ("OCRD", "clase_de_socio_de_negocios"): "card_type",
    ("OCRD", "codigo_de_grupo"): "grp_code",
    # OITM: ItemCode, ItemName, ItmsGrpCod
    ("OITM", "numero_de_articulo"): "item_code",
    ("OITM", "descripcion_del_articulo"): "item_name",
    ("OITM", "grupo_de_articulos"): "items_grp_cod",
    # OITB: ItmsGrpCod, ItmsGrpNam
    ("OITB", "numero"): "itms_grp_cod",
    ("OITB", "nombre_de_grupo"): "itms_grp_nam",
    # ITM1: ItemCode + PriceList
    ("ITM1", "numero_de_articulo"): "item_code",
    ("ITM1", "numero_de_lista_de_precios"): "price_list",
    # OITW: ItemCode + WhsCode
    ("OITW", "numero_de_articulo"): "item_code",
    ("OITW", "codigo_de_almacen"): "whs_code",
    # OBTN: ItemCode + SysNumber + DistNumber
    ("OBTN", "numero_de_articulo"): "item_code",
    ("OBTN", "numero_de_sistema"): "sys_number",
    ("OBTN", "numero_de_lote"): "dist_number",
    # OBTQ: ItemCode + SysNumber + WhsCode
    ("OBTQ", "numero_de_articulo"): "item_code",
    ("OBTQ", "numero_de_sistema"): "sys_number",
    ("OBTQ", "codigo_de_almacen"): "whs_code",
    # OACT: AcctCode, AcctName
    ("OACT", "codigo_de_cuenta"): "acct_code",
    ("OACT", "nombre_de_cuenta"): "acct_name",
    # OJDT: TransId, RefDate (en export ES: "Numero de operacion" es TransId,
    # "Numero de comprobante de diario" es BatchNum)
    ("OJDT", "numero_de_operacion"): "trans_id",
    ("OJDT", "numero_de_comprobante_de_diario"): "batch_num",
    ("OJDT", "fecha_de_contabilizacion"): "ref_date",
    # JDT1: TransId + Line_ID
    ("JDT1", "clave_de_operacion"): "trans_id",
    ("JDT1", "numero_de_linea"): "line_id",
    ("JDT1", "codigo_de_cuenta"): "acct_code",
    # ORDR / OPOR / OINV / OPCH: cabeceras de docs
    # Ojo: "/" se vuelve "_" en slugify => codigo_de_cliente_proveedor
    ("ORDR", "numero_interno"): "doc_entry",
    ("ORDR", "numero_de_documento"): "doc_num",
    ("ORDR", "fecha_de_contabilizacion"): "doc_date",
    ("ORDR", "codigo_de_cliente_proveedor"): "card_code",
    ("ORDR", "nombre_de_cliente_proveedor"): "card_name",
    # OPOR usa "Numerador" en lugar de "Numero interno"
    ("OPOR", "numerador"): "doc_entry",
    ("OPOR", "numero_de_documento"): "doc_num",
    ("OPOR", "fecha_de_contabilizacion"): "doc_date",
    ("OPOR", "codigo_de_cliente_proveedor"): "card_code",
    ("OPOR", "nombre_de_cliente_proveedor"): "card_name",
    ("OINV", "numero_interno"): "doc_entry",
    ("OINV", "numero_de_documento"): "doc_num",
    ("OINV", "fecha_de_contabilizacion"): "doc_date",
    ("OINV", "codigo_de_cliente_proveedor"): "card_code",
    ("OINV", "nombre_de_cliente_proveedor"): "card_name",
    ("OPCH", "numero_interno"): "doc_entry",
    ("OPCH", "numero_de_documento"): "doc_num",
    ("OPCH", "fecha_de_contabilizacion"): "doc_date",
    ("OPCH", "codigo_de_cliente_proveedor"): "card_code",
    ("OPCH", "nombre_de_cliente_proveedor"): "card_name",
    # Lineas RDR1, POR1, INV1, PCH1: DocEntry + LineNum + ItemCode
    ("RDR1", "id_interno_de_documento"): "doc_entry",
    ("RDR1", "numero_de_linea"): "line_num",
    ("RDR1", "numero_de_articulo"): "item_code",
    ("RDR1", "codigo_de_almacen"): "whs_code",
    ("RDR1", "cantidad"): "quantity",
    ("POR1", "id_interno_de_documento"): "doc_entry",
    ("POR1", "numero_de_linea"): "line_num",
    ("POR1", "numero_de_articulo"): "item_code",
    ("POR1", "codigo_de_almacen"): "whs_code",
    ("POR1", "cantidad"): "quantity",
    ("INV1", "id_interno_de_documento"): "doc_entry",
    ("INV1", "numero_de_linea"): "line_num",
    ("INV1", "numero_de_articulo"): "item_code",
    ("INV1", "codigo_de_almacen"): "whs_code",
    ("INV1", "cantidad"): "quantity",
    ("PCH1", "id_interno_de_documento"): "doc_entry",
    ("PCH1", "numero_de_linea"): "line_num",
    ("PCH1", "numero_de_articulo"): "item_code",
    ("PCH1", "codigo_de_almacen"): "whs_code",
    ("PCH1", "cantidad"): "quantity",
}


def slugify(text: str) -> str:
    """ES → snake_case ascii. Determinista, sin colisiones esperadas dentro de una tabla."""
    # Quitar BOM y espacios
    text = text.replace("﻿", "").strip()
    # Normalizar acentos
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lower
    s = no_accents.lower()
    # Remplazar caracteres no alfanumericos por _
    s = re.sub(r"[^a-z0-9]+", "_", s)
    # Trim _ extremos
    s = s.strip("_")
    if not s:
        s = "col"
    return s


def disambiguate(slugs: list[str]) -> list[str]:
    """Si hay duplicados despues del slugify, agrega _2, _3, etc."""
    counts: dict[str, int] = {}
    out: list[str] = []
    for s in slugs:
        if s not in counts:
            counts[s] = 1
            out.append(s)
        else:
            counts[s] += 1
            out.append(f"{s}_{counts[s]}")
    return out


def read_headers(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def build_mapping() -> dict:
    mapping: dict = {}
    for table in TABLES:
        csv_path = RAW / f"{table}_{DATE_TAG}.csv"
        if not csv_path.exists():
            print(f"WARNING: no encontrado {csv_path}", file=sys.stderr)
            continue
        headers = read_headers(csv_path)
        # Slugify base
        base_slugs = [slugify(h) for h in headers]
        # Override por PK conocido y por fechas de watermark
        slugs = []
        for orig, slug in zip(headers, base_slugs):
            key = (table, slug)
            if key in PK_OVERRIDES:
                slugs.append(PK_OVERRIDES[key])
            elif slug in DATE_OVERRIDES:
                slugs.append(DATE_OVERRIDES[slug])
            else:
                slugs.append(slug)
        # Resolver colisiones (incluyendo despues de override)
        slugs = disambiguate(slugs)
        # Ensamblar dict ordenado preservando orden de columnas
        table_map = {}
        for orig, slug in zip(headers, slugs):
            # Limpiar BOM del key
            clean_orig = orig.replace("﻿", "")
            table_map[clean_orig] = slug
        mapping[table] = table_map
        print(f"  {table}: {len(headers)} columnas")
    return mapping


def main() -> None:
    print(f"Leyendo headers desde {RAW}")
    mapping = build_mapping()

    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG.open("w", encoding="utf-8") as f:
        f.write("# Mapping ES -> snake_case por tabla SAP B1.\n")
        f.write("# Generado por scripts/build_header_mapping.py.\n")
        f.write("# PKs canonicos overridean al slugify automatico (ver PK_OVERRIDES).\n\n")
        yaml.safe_dump(
            mapping,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=200,
        )
    total = sum(len(v) for v in mapping.values())
    print(f"\nOK -> {CONFIG} ({len(mapping)} tablas, {total} columnas)")


if __name__ == "__main__":
    main()
