-- INV1 — Facturas a clientes (detalle)
-- Exportar a: INV1_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT D.*
FROM INV1 D
INNER JOIN OINV H ON H.DocEntry = D.DocEntry
WHERE H.DocDate >= @SINCE
   OR H.UpdateDate >= @SINCE
ORDER BY D.DocEntry, D.LineNum;
