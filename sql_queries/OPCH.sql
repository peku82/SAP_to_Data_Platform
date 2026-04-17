-- OPCH — Facturas de proveedor (cabecera)
-- Exportar a: OPCH_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT *
FROM OPCH
WHERE DocDate >= @SINCE
   OR UpdateDate >= @SINCE
ORDER BY DocEntry;
