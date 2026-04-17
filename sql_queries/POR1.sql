-- POR1 — Órdenes de compra (detalle)
-- Exportar a: POR1_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT R.*
FROM POR1 R
INNER JOIN OPOR H ON H.DocEntry = R.DocEntry
WHERE H.DocDate >= @SINCE
   OR H.UpdateDate >= @SINCE
ORDER BY R.DocEntry, R.LineNum;
