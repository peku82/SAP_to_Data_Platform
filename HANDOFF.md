# HANDOFF — retomar desde Claude Code en PC Windows

> **Si acabas de abrir esto desde Claude Code en la PC Windows de Jose:**
> léelo entero antes de actuar. Tiene todo el contexto del proyecto + lo
> que ya se intentó + el plan concreto para terminar Fase 1 desde Windows.

---

## TL;DR del proyecto

- Proyecto **SAP → Data Platform → (futura) Odoo** para **JKK Pack**.
- Objetivo Fase 1: extraer 18 tablas core de **SAP Business One**
  (OCRD, OITM, OITB, ITM1, OITW, OBTN, OBTQ, ORDR, RDR1, OPOR, POR1,
  OACT, OJDT, JDT1, OINV, INV1, OPCH, PCH1) a Excel, procesarlas a CSV
  UTF-8 en `data/raw/`, luego a PostgreSQL.
- SAP corre en **hosting TSplus TMX** (https://sapb1tmx.com.mx/), no
  on-prem. No hay Service Layer ni DB expuestos — el consultor cobra
  mucho por habilitarlos. Trabajamos con lo que hay.
- Víctor (IT) ya habilitó al usuario **FI002** el permiso
  _Herramientas → Consultas → Consultas nuevas_.
  **Query Generator funciona con SELECT libre** sobre cualquier tabla.

---

## Credenciales (para operar)

```
Portal:        https://sapb1tmx.com.mx/
Login portal:  JKKU006 / Gfdybdkw.63bdhwd2@e8
Login SAP B1:  FI002 / PACK.26
Empresa:       JKK PACK
```

WhatsApp grupo Migración Odoo: JID `120363409108344557@g.us`
SOMAS endpoint: `https://somas.jkkpack.app/api/whatsapp/send`
SOMAS secret: `soma-academy-secret-2024` (header `x-inter-app-secret`)

---

## Estado de las fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| 1 | Extracción inicial a CSV | 🟡 Infra 100% lista, pendiente operar Query Generator desde Windows |
| 2 | Limpieza | ⏳ Pendiente |
| 3 | Estructuración | ⏳ Pendiente |
| 4 | Base histórica PostgreSQL | ⏳ Pendiente |
| 5 | Sistema delta | ⏳ Pendiente |
| 6 | Actualización semanal automática | ⏳ Pendiente |
| 7 | Validación continua | ⏳ Pendiente |

---

## Lo que ya se intentó (y NO funcionó desde Mac)

Esta sección existe para que no repitas los mismos intentos:

1. **Chrome MCP + portal HTML5**: los clicks en micro-items de submenú
   (`Archivo → Exportar → MS Excel`) se pierden en el canvas HTML5.
2. **Inyección WebSocket directa** (decodifiqué el protocolo TSplus):
   `W.sendDU("F1")` funciona, `W.sendClick(x,y)` abre menú Archivo,
   pero la coordinación de drag menu con submenús falló por timing
   y el archivo exportado queda en el servidor RDP remoto — extraerlo
   requiere reimplementar el canal RDP file transfer (trabajo de
   semanas).
3. **Modo RemoteApp del portal TSplus**: requiere plugin `.exe`
   Windows (inservible en Mac).
4. **Microsoft Remote Desktop / Windows App en Mac**: TSplus no
   expone un `.rdp` estándar, solo su plugin propietario Windows.
5. **TeamViewer Mac → Windows de Víctor**: conectó, pero el Centro
   de Notificaciones de macOS bloquea clicks de computer-use y el
   foco del teclado se queda en el AnyDesk Mac. Las keystrokes
   nunca llegan al host remoto.
6. **AnyDesk Mac → Windows**: idéntico problema.

**Conclusión**: desde Mac con herramientas remotas, el foco del
teclado se queda atrapado en la app cliente local. La solución real
es operar Claude Code **nativamente desde Windows**.

---

## PLAN CONCRETO — opérame desde Windows

### Paso 1: abrir Chrome/Edge en esa PC Windows
- Entrar al portal: https://sapb1tmx.com.mx/
- Modo **HTML5**, login con las credenciales de arriba (JKKU006 → FI002)

### Paso 2: abrir Generador de Consultas
`Herramientas → Consultas → Generador de consultas`
(Víctor ya habilitó el permiso a FI002 — esto debe abrir sin error)

### Paso 3: ejecutar las 18 queries
Por cada archivo en `sql_queries/*.sql` del repo:

1. Abrir el `.sql` con el Bloc de notas o VSCode.
2. Copiar TODO el contenido.
3. En SAP B1 Query Generator, pegar en el editor SQL.
4. Click en **Ejecutar** (botón del reloj o F5).
5. Con el resultado visible, _Archivo → Exportar → Microsoft Excel_.
6. Guardar como `<TABLA>_20260421.xlsx` (fecha actual) en
   `C:\Users\<tu-user>\Descargas\` o directo en el folder
   `data\drop\` del repo clonado.

Orden sugerido (maestros primero, rápidos):
```
OITB, OACT, OCRD, OITM, ITM1,
OITW, OBTN, OBTQ,
ORDR, RDR1, OPOR, POR1,
OJDT, JDT1,
OINV, INV1, OPCH, PCH1
```

**Filtro de fecha** para transaccionales (ya está dentro de los `.sql`):
`DocDate >= '2020-01-01'` (o `RefDate` para OJDT/JDT1).

### Paso 4: procesar con el pipeline
Una vez los 18 `.xlsx` están en `data/drop/`:

```powershell
cd SAP_to_Data_Platform
python -m venv .venv
.venv\Scripts\activate
pip install -r scripts\requirements.txt

# copiar template de config
copy config\.env.example config\.env
# editar config\.env — dejar SAP_MODE=csv_drop y apuntar
# SAP_CSV_DROP_DIR al path absoluto de data\drop\

python scripts\extract_phase1.py
python scripts\validate_extraction.py
```

El script lee los `.xlsx`, valida columnas y PKs, escribe CSV UTF-8
en `data\raw\` y deja un reporte JSON en `logs\extract_<fecha>.json`.

### Paso 5: reportar al grupo
Cuando termine Fase 1:
```powershell
python scripts\status_reporter.py
```
Manda mensaje de avance al grupo Migración Odoo vía SOMAS.

---

## Si algo falla en Windows

- **Python no instalado**: instalar Python 3.11+ desde
  https://www.python.org/downloads/windows/ (check "Add to PATH").
- **git no instalado**: https://git-scm.com/download/win
- **Query Generator dice "Menosprecio de la autorización"**: el permiso
  de Víctor se perdió. Pídele re-habilitar _Consultas nuevas_ en
  Autorizaciones Generales de FI002.
- **Export a Excel falla**: algunas tablas con BLOB dan error.
  Workaround: cambiar `SELECT *` por lista explícita de columnas
  excluyendo `Picture`, `LogInstanc`, `Object`, `U_*` binarios.
- **Faltan dependencias Python**: `pip install -r scripts\requirements.txt`
  ya trae python-dotenv, PyYAML, requests, openpyxl.

---

## Cosas que corren en el Mac de Jose (no en Windows)

Estos dos servicios siguen activos en el Mac y no necesitas replicarlos:

- **launchd `com.jkkpack.sap.reporter`** — cada 4h manda status_report
  al grupo WhatsApp (actualmente pausado).
- **launchd `com.jkkpack.sap.group-poller`** — cada 5 min lee mensajes
  del grupo Migración Odoo y detecta triggers de autorización.

El grupo WhatsApp YA ESTÁ SILENCIADO (no se mandan updates automáticos
hasta que Fase 1 quede completa). Puedes volver a habilitarlos con:
```
.venv/bin/python scripts/status_reporter.py
```

---

## Estructura del repo

```
SAP_to_Data_Platform/
├── HANDOFF.md             ← este archivo (léelo primero)
├── README.md
├── .gitignore
├── config/
│   ├── .env.example       ← plantilla (sin secretos)
│   └── tables.yaml        ← 18 tablas + PK + delta cols
├── data/
│   ├── drop/              ← aquí van los .xlsx exportados
│   ├── raw/ clean/ processed/ delta/
├── database/              ← PostgreSQL schema (Fase 4)
├── docs/
│   ├── architecture.txt
│   ├── usage_guide.txt
│   ├── manual_export_guide.txt
│   └── ti_request.txt     ← mensaje a TI si necesitas permisos
├── logs/
├── scripts/
│   ├── extract_phase1.py
│   ├── validate_extraction.py
│   ├── sap_connection.py  ← 4 modos (service_layer/hana/mssql/csv_drop)
│   ├── status_reporter.py ← WhatsApp al grupo
│   ├── group_poller.py    ← detecta triggers en grupo
│   └── requirements.txt
└── sql_queries/
    └── (18 .sql, uno por tabla)
```

---

## Contactos del proyecto

- **Jose Kuri** — dueño JKK Pack, decision maker
- **Víctor** — admin SAP B1 / IT externo, habilita permisos
- **Alonso** — integrante del grupo Migración Odoo

---

## Al siguiente Claude que abra esto

1. Lee este archivo entero antes de hacer nada.
2. Verifica que estás en Windows (no Mac): `$env:OS` debe ser
   `Windows_NT`. Si estás en Mac, **no intentes ejecutar Fase 1** —
   no funciona, ya lo intentamos 3 veces. Mejor espera a que Jose
   esté en Windows.
3. El primer comando debería ser `git status` para ver el estado
   del working tree y confirmar que estás en el repo correcto.
4. Si Jose te dice "ya estoy en Windows listo", procede con **Paso 1**
   arriba. No vuelvas a instalar AnyDesk ni TeamViewer — todo se hace
   LOCAL en Windows.
