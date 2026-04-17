data/delta/
===========

Deltas semanales (Fase 5). Cada corrida detecta cambios usando:

  - UpdateDate  (modificaciones)
  - DocDate     (fecha del documento)
  - CreateDate  (alta del registro)

contra el watermark guardado en:
  ../../logs/watermarks.json

Archivos:
  <TABLA>_delta_<YYYYMMDD>.csv   — solo registros nuevos o modificados

Cada delta tiene un reporte:
  <TABLA>_delta_<YYYYMMDD>.json
con:
  - rango de fechas consultado
  - watermark anterior / nuevo
  - conteo de altas / modificaciones
  - duración de la extracción

Reglas:
  - NUNCA editar watermarks.json a mano sin respaldo previo
  - un delta se considera aplicado solo cuando su JSON tiene status=applied
