scripts/
========

Scripts Python del pipeline. Todos usan el mismo .env en ../config/.env.

Fase 1 — Extracción:
  sap_connection.py       Helper de conexión. Soporta 3 modos:
                            - Service Layer (REST, default)
                            - HANA directo
                            - MSSQL directo
  extract_phase1.py       Extrae las 20 tablas a ../data/raw/
  validate_extraction.py  Valida completitud (count vs. SAP) y detecta
                          truncamientos.

Reportes:
  status_reporter.py      Genera logs/status_report.txt + envía por
                          WhatsApp al +52 1 55 2653 9904 vía SOMAS.

Próximos (Fases 2-7, pendientes):
  clean_phase2.py
  structure_phase3.py
  load_db_phase4.py
  delta_phase5.py
  weekly_phase6.sh
  validate_phase7.py

Uso:
  python scripts/extract_phase1.py
  python scripts/validate_extraction.py
  python scripts/status_reporter.py

Dependencias: ver requirements.txt
