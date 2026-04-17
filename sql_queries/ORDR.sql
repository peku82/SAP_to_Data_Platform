-- ORDR — Pedidos de cliente (cabecera)
-- Filtro por fecha para no traer toda la historia en la primera carga.
-- Ajusta @SINCE si quieres traer más o menos historia.
-- Exportar a: ORDR_<YYYYMMDD>.xlsx

DECLARE @SINCE DATE = '2020-01-01';

SELECT *
FROM ORDR
WHERE DocDate >= @SINCE
   OR UpdateDate >= @SINCE
ORDER BY DocEntry;
