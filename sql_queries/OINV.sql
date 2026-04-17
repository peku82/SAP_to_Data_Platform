-- OINV — Facturas a clientes (cabecera)
-- Exportar a: OINV_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT *
FROM OINV
WHERE DocDate >= @SINCE
   OR UpdateDate >= @SINCE
ORDER BY DocEntry;
