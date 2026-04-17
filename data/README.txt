DATA/
=====

Carpeta con todos los datasets del pipeline, en orden de maduración:

raw/        — CSV exportados tal cual desde SAP (Fase 1). No modificar.
clean/      — CSV normalizados: sin duplicados, SKUs validados, textos
              homologados, nulos críticos marcados (Fase 2).
processed/  — CSV con claves consistentes entre tablas y estructura
              uniforme lista para cargar a PostgreSQL (Fase 3).
delta/      — Deltas semanales: solo registros nuevos/modificados
              detectados por UpdateDate/DocDate/CreateDate (Fase 5).

Convención de nombres:
  <TABLA>_<YYYYMMDD>.csv           ejemplo: OITM_20260417.csv
  <TABLA>_delta_<YYYYMMDD>.csv     ejemplo: ORDR_delta_20260420.csv

Encoding: UTF-8 con BOM.
Separador: coma (,).
Quote: comillas dobles (") con escape duplicado.
