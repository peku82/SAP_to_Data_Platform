logs/
=====

Bitácora completa del pipeline. Todos los scripts escriben aquí.

Archivos:
  status_report.txt              — reporte de avance actual (se sobrescribe
                                   cada 4h y se envía por WhatsApp)
  status_report_<YYYYMMDD_HHMM>  — snapshots históricos del status_report
  extract_<YYYYMMDD>.log         — log detallado de cada ejecución Fase 1
  validate_<YYYYMMDD>.log        — log de validación post-extracción
  watermarks.json                — última UpdateDate por tabla (para deltas)
  errors.log                     — errores críticos acumulados

Rotación:
  - status_report_*.txt se conservan 90 días
  - extract_*.log se conservan 180 días
  - errors.log se rota mensualmente a errors_<YYYYMM>.log

Acceso:
  El script status_reporter.py puede ser ejecutado manualmente o por cron
  cada 4 horas. Envía al +52 1 55 2653 9904 vía SOMAS.
