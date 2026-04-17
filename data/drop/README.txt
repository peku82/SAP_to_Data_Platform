data/drop/
==========

CARPETA DE ENTRADA (buzón) — aquí cae todo lo exportado desde SAP B1.

Procedimiento:
  1. El operador ejecuta en SAP B1 Query Manager cada .sql de sql_queries/.
  2. Exporta el resultado a Excel con el nombre exacto:
        <TABLA>_<YYYYMMDD>.xlsx
     Ejemplos:
        OITM_20260417.xlsx
        ORDR_20260417.xlsx
  3. Guarda el archivo en esta carpeta (o en la carpeta sincronizada
     Google Drive/OneDrive que apunta aquí — ver SAP_CSV_DROP_DIR).
  4. En la máquina con el pipeline:
        python scripts/extract_phase1.py
     El script toma el archivo MÁS RECIENTE por tabla, lo convierte a
     CSV UTF-8 y lo mueve a data/raw/.

Importante:
  - Si dejas varios archivos de la misma tabla con fechas diferentes,
    el script toma el más reciente por fecha de modificación.
  - No borres los archivos viejos inmediatamente, sirven como respaldo.
  - Acepta .xlsx, .xls y .csv indistintamente.

Si el archivo tiene nombre incorrecto (sin fecha, sin guión bajo, etc.)
el script lo ignora silenciosamente. Revisar logs/extract_<fecha>.log.
