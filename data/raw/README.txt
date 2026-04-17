data/raw/
=========

CSV exportados TAL CUAL desde SAP Business One. Esta es la "fuente de verdad
cruda". Cualquier análisis debe derivar de aquí.

REGLA: nada se edita manualmente. Si hay problema, se re-extrae.

Fase 1 extrae estas tablas:

MAESTROS:
  OCRD — Socios de negocio (clientes y proveedores)
  OITM — Artículos / productos
  OITB — Grupos de artículos
  ITM1 — Listas de precios por artículo

INVENTARIO:
  OITW — Artículos por almacén
  OBTN — Lotes
  OBTQ — Cantidades de lote por almacén

OPERACIONES:
  ORDR / RDR1 — Pedidos de cliente (cabecera / detalle)
  OPOR / POR1 — Órdenes de compra (cabecera / detalle)

CONTABILIDAD:
  OACT — Catálogo de cuentas
  OJDT / JDT1 — Asientos contables (pólizas)

HISTÓRICO:
  OINV / INV1 — Facturas de clientes (cabecera / detalle)
  OPCH / PCH1 — Facturas de proveedor (cabecera / detalle)

Cada ejecución crea: <TABLA>_<YYYYMMDD>.csv
Metadata de cada extracción queda en: ../../logs/extract_<YYYYMMDD>.log
