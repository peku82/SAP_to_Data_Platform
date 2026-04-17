-- OJDT — Pólizas / asientos contables (cabecera)
-- Filtro por RefDate (fecha contable).
-- Exportar a: OJDT_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT *
FROM OJDT
WHERE RefDate >= @SINCE
   OR UpdateDate >= @SINCE
ORDER BY TransId;
