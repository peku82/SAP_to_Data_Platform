-- JDT1 — Pólizas / asientos contables (detalle)
-- Exportar a: JDT1_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT D.*
FROM JDT1 D
INNER JOIN OJDT H ON H.TransId = D.TransId
WHERE H.RefDate >= @SINCE
   OR H.UpdateDate >= @SINCE
ORDER BY D.TransId, D.Line_ID;
