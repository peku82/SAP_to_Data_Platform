data/clean/
===========

CSV limpios (Fase 2). Se generan a partir de data/raw/ aplicando:

  - eliminación de duplicados exactos
  - validación de SKUs (formato, longitud, caracteres válidos)
  - normalización de textos (trim, acentos, mayúsculas donde aplique)
  - homologación de unidades de medida
  - detección y marcado de nulos críticos
  - tipos de dato explícitos (fechas ISO, decimales con punto)

Cada archivo tiene un reporte de calidad hermano:
  <TABLA>_<YYYYMMDD>_quality.json

El reporte incluye:
  - filas leídas / filas escritas / filas descartadas
  - lista de reglas aplicadas
  - conteo de nulos por columna crítica
  - top 10 valores anómalos
