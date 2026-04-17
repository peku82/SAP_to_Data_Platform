-- PCH1 — Facturas de proveedor (detalle)
-- Exportar a: PCH1_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT D.*
FROM PCH1 D
INNER JOIN OPCH H ON H.DocEntry = D.DocEntry
WHERE H.DocDate >= @SINCE
   OR H.UpdateDate >= @SINCE
ORDER BY D.DocEntry, D.LineNum;
