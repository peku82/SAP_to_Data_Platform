-- OBTN — Lotes (batch numbers)
-- Exportar a: OBTN_<YYYYMMDD>.xlsx

SELECT * FROM OBTN ORDER BY ItemCode, SysNumber;
