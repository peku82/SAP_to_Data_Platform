-- RDR1 — Pedidos de cliente (detalle)
-- Filtramos usando JOIN a ORDR para respetar el mismo @SINCE.
-- Exportar a: RDR1_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT R.*
FROM RDR1 R
INNER JOIN ORDR H ON H.DocEntry = R.DocEntry
WHERE H.DocDate >= @SINCE
   OR H.UpdateDate >= @SINCE
ORDER BY R.DocEntry, R.LineNum;
