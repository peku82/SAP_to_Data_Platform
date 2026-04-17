database/
=========

Base histórica PostgreSQL (Fase 4).

Contiene:
  schema.sql              — DDL con tablas e índices
  init_db.sh              — script idempotente que crea DB y ejecuta schema.sql
  load_from_processed.py  — carga masiva COPY desde data/processed/
  dumps/                  — pg_dump comprimidos por fecha (backup)

Tablas principales (ver schema.sql para detalle):
  socios_negocio          — OCRD
  articulos               — OITM + OITB + ITM1
  inventario              — OITW + OBTN + OBTQ
  ordenes_venta           — ORDR + RDR1
  ordenes_compra          — OPOR + POR1
  polizas                 — OJDT + JDT1
  facturas_clientes       — OINV + INV1
  facturas_proveedor      — OPCH + PCH1
  cuentas_contables       — OACT

Índices obligatorios:
  - idx_articulos_sku              (articulos.item_code)
  - idx_socios_cardcode            (socios_negocio.card_code)
  - idx_facturas_cli_fecha         (facturas_clientes.doc_date)
  - idx_facturas_cli_cliente       (facturas_clientes.card_code)
  - idx_facturas_prov_fecha        (facturas_proveedor.doc_date)
  - idx_polizas_fecha              (polizas.ref_date)

Configuración por defecto:
  host:   localhost
  port:   5432
  db:     sap_historico
  user:   sap_reader
  (ver config/.env para credenciales reales)
