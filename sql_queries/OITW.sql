-- OITW — Artículos por almacén (stock actual)
-- Exportar a: OITW_<YYYYMMDD>.xlsx

SELECT * FROM OITW ORDER BY ItemCode, WhsCode;
