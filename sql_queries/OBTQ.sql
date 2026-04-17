-- OBTQ — Cantidades de lote por almacén
-- Exportar a: OBTQ_<YYYYMMDD>.xlsx

SELECT * FROM OBTQ ORDER BY ItemCode, SysNumber, WhsCode;
