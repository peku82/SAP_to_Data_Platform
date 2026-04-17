sql_queries/
============

18 consultas SQL listas para pegar en SAP B1 — Query Manager.

CÓMO USAR
---------
1. Entrar a https://sapb1tmx.com.mx/ con JKKU006.
2. En SAP B1 cliente (FI002 / PACK.26):
     Herramientas → Consultas → Generador de Consultas
     (Tools → Queries → Query Manager)
3. Borrar el contenido del editor.
4. Copiar el contenido de <TABLA>.sql y pegar.
5. Ejecutar (botón con el reloj o tecla F5).
6. Con el resultado visible:
     Archivo → Exportar → Microsoft Excel
   y guardar como:
     <TABLA>_<YYYYMMDD>.xlsx    (ejemplo: OITM_20260417.xlsx)
7. Guardar en la carpeta compartida cuya ruta local está en
   SAP_CSV_DROP_DIR del .env.

ORDEN SUGERIDO PARA UNA PRIMERA CARGA
-------------------------------------
Maestros primero (pocos registros, rápido):
  OITB, OACT, OCRD, OITM, ITM1

Inventario:
  OITW, OBTN, OBTQ

Transaccionales (usan filtro de fecha SINCE — ajustar el año):
  ORDR, RDR1, OPOR, POR1, OINV, INV1, OPCH, PCH1, OJDT, JDT1

FILTRO DE FECHA
---------------
Todas las consultas transaccionales tienen al inicio:
  DECLARE @SINCE DATE = '2020-01-01';
Cambia la fecha si quieres traer menos historia.

SOPORTE HANA vs SQL SERVER
--------------------------
Cada .sql está escrito en T-SQL (SQL Server), que es el dialecto de
SAP B1 on-SQL. Si este SAP corre sobre HANA, las adaptaciones son
mínimas (sintaxis de fecha y LEN/LENGTH). Si el Query Manager da error
de sintaxis, avisa y generamos la versión HANA.

INDICE
------
Maestros:
  OCRD.sql   Socios de negocio
  OITM.sql   Artículos
  OITB.sql   Grupos de artículos
  ITM1.sql   Precios por lista de precio

Inventario:
  OITW.sql   Artículos por almacén
  OBTN.sql   Lotes
  OBTQ.sql   Cantidades de lote por almacén

Operaciones:
  ORDR.sql   Pedidos de cliente — cabecera
  RDR1.sql   Pedidos de cliente — detalle
  OPOR.sql   Órdenes de compra — cabecera
  POR1.sql   Órdenes de compra — detalle

Contabilidad:
  OACT.sql   Catálogo de cuentas
  OJDT.sql   Pólizas — cabecera
  JDT1.sql   Pólizas — detalle

Histórico:
  OINV.sql   Facturas cliente — cabecera
  INV1.sql   Facturas cliente — detalle
  OPCH.sql   Facturas proveedor — cabecera
  PCH1.sql   Facturas proveedor — detalle
