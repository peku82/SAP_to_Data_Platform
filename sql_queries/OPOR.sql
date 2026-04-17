-- OPOR — Órdenes de compra (cabecera)
-- Exportar a: OPOR_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT *
FROM OPOR
WHERE DocDate >= @SINCE
   OR UpdateDate >= @SINCE
ORDER BY DocEntry;
