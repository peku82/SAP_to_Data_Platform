# SAP_to_Data_Platform

Pipeline de datos read-only desde **SAP Business One** a una plataforma de datos
propia (PostgreSQL + CSV histórico) con sistema de deltas semanales.

Proyecto para **JKK Pack**. Preparado para futura migración a Odoo (no se ejecuta
aún).

---

## Estado del proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Extracción inicial a CSV | 🟡 Infraestructura lista, pendiente endpoint SAP |
| 2 | Limpieza | ⏳ Pendiente |
| 3 | Estructuración | ⏳ Pendiente |
| 4 | Base histórica PostgreSQL | ⏳ Pendiente |
| 5 | Sistema delta | ⏳ Pendiente |
| 6 | Actualización semanal automática | ⏳ Pendiente |
| 7 | Validación continua | ⏳ Pendiente |

---

## Estructura

```
SAP_to_Data_Platform/
├── data/
│   ├── raw/        # CSV crudos directos de SAP (Fase 1)
│   ├── clean/      # CSV limpios (Fase 2)
│   ├── processed/  # CSV relacionados y homologados (Fase 3)
│   └── delta/      # Deltas semanales (Fase 5)
├── database/       # Dumps PostgreSQL + esquema (Fase 4)
├── scripts/        # Scripts Python del pipeline
├── logs/           # Logs de ejecución + status_report.txt
├── docs/           # Documentación técnica
└── config/         # .env y parámetros de conexión
```

---

## Arranque rápido

```bash
cd ~/claude/SAP_to_Data_Platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# Copiar plantilla de configuración y editar con credenciales reales
cp config/.env.example config/.env
nano config/.env

# Ejecutar Fase 1
python scripts/extract_phase1.py

# Enviar reporte de estado manual
python scripts/status_reporter.py
```

---

## Acceso SAP actual (documentado)

**Tipo:** Portal TSplus RemoteApp/HTML5 (gateway RDP).
**URL:** https://sapb1tmx.com.mx/
**Usuarios read-only:**
- Portal: `JKKU006`
- SAP B1 cliente: `FI002`

> Este tipo de acceso **NO permite extracción programática directa**.
> Ver `docs/architecture.txt` para el plan técnico y los endpoints que TI debe
> habilitar (Service Layer, HANA direct, o exportación DB read-only).

---

## Reportes automáticos

Cada 4 horas se genera `logs/status_report.txt` y se envía por WhatsApp al
`+52 1 55 2653 9904` a través del endpoint de SOMAS.

---

## Entregables

Ver `docs/usage_guide.txt` para la guía completa de uso.
