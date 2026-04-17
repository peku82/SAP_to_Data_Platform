data/processed/
===============

CSV con estructura final lista para cargar a PostgreSQL (Fase 3).

Aquí se garantiza:
  - claves primarias consistentes (CardCode, ItemCode, DocEntry...)
  - foreign keys verificadas (ej: RDR1.DocEntry referencia ORDR.DocEntry)
  - columnas homogeneizadas entre cabecera y detalle
  - columnas calculadas estables: importes con IVA, márgenes, rotación
  - snake_case en nombres de columna para PostgreSQL

Nombres de tabla (destino):
  socios_negocio
  articulos
  facturas_clientes
  facturas_clientes_detalle
  facturas_proveedor
  facturas_proveedor_detalle
  ordenes_venta / ordenes_venta_detalle
  ordenes_compra / ordenes_compra_detalle
  polizas / polizas_detalle
  inventario_almacen
  lotes
