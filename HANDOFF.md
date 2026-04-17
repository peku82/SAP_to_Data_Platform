# Handoff — retomar desde PC Windows (lunes)

> Para retomar el proyecto desde otra máquina (la PC Windows de Jose) y
> no empezar de cero. Pégale esto completo a tu nuevo Claude Code.

---

## Contexto de alto nivel

Proyecto: **SAP → Data Platform → (futura) Odoo** para **JKK Pack**.
Extraer las 18 tablas core de SAP Business One a una base histórica
PostgreSQL fuera de SAP, con deltas semanales y preparación para
migración futura a Odoo.

SAP Business One corre en **hosting TSplus TMX** (no on-prem):
- URL portal: https://sapb1tmx.com.mx/
- Login portal: `JKKU006` / `Gfdybdkw.63bdhwd2@e8`
- Usuario SAP: `FI002` / `PACK.26` (company: JKK PACK)

**No hay Service Layer ni DB directa** (el consultor cobra mucho por
habilitarlos). Trabajamos con lo que hay.

---

## Estado actual (2026-04-17)

### Lo que está listo y funcionando
- ✅ Estructura completa del proyecto en `SAP_to_Data_Platform/`
- ✅ **18 consultas SQL** listas en `sql_queries/` (una por tabla)
- ✅ Pipeline Python `scripts/extract_phase1.py` — ingesta .xlsx/.csv
      desde `data/drop/`, normaliza a CSV UTF-8 en `data/raw/`
- ✅ `scripts/validate_extraction.py` — valida filas, duplicados de PK
- ✅ `scripts/status_reporter.py` — genera logs/status_report.txt y
      envía por WhatsApp al grupo **Migración Odoo**
      (JID `120363409108344557@g.us`) vía SOMAS
- ✅ `scripts/group_poller.py` — poleo cada 5 min del grupo WhatsApp,
      detecta triggers ("listo", "autorizado", etc) y deja flag en
      `logs/victor_authorized.flag`
- ✅ `scripts/sap_connection.py` — conector con 4 modos
      (service_layer / hana / mssql / csv_drop). Hoy se usa `csv_drop`.
- ✅ Docs completos en `docs/` (architecture.txt, usage_guide.txt,
      manual_export_guide.txt, ti_request.txt)

### Lo que TI habilitó
- ✅ Víctor (IT) habilitó al usuario FI002 el permiso
      _Herramientas → Consultas → Consultas nuevas_ en SAP B1.
      **Query Generator funciona** con SELECT libre sobre cualquier tabla.

### Lo que bloqueó el avance desde Mac
- ❌ Portal TSplus modo **HTML5** renderiza SAP como canvas streaming.
      Los clicks programáticos en **submenús pequeños** (Archivo →
      Exportar → MS Excel) se pierden en el canvas HTML5.
- ❌ Portal modo **RemoteApp** requiere plugin .exe Windows, inservible
      en Mac.
- ❌ Aunque disparáramos export, el .xlsx queda en el servidor RDP
      remoto — extraerlo requiere reimplementar canal RDP de file
      transfer.

### Plan para retomar desde PC Windows
Abrir el portal TSplus HTML5 desde **Windows nativo** (Chrome/Edge
en tu PC ARM). Ahí los clicks son eventos trusted del OS → menús
funcionan normal → `Archivo → Exportar → MS Excel` guarda el .xlsx
directo en `Descargas\`. Yo me conecto remoto a tu PC para operarla
(ver "Cómo conectamos" abajo).

---

## Cómo conectamos el lunes (opciones)

### A) AnyDesk (lo más fácil para ti)
1. En tu PC Windows, descarga e instala **AnyDesk**
   (https://anydesk.com — gratis para uso personal).
2. Al abrirlo muestra un **código de 9 dígitos** (tu ID de AnyDesk).
3. Me pasas ese ID + una contraseña que tú pones.
4. Yo me conecto desde mi Mac, controlo tu pantalla.
**Ventaja**: no configuras nada de red; funciona atrás de cualquier
firewall/router.

### B) TeamViewer (misma idea, alternativa)
Similar a AnyDesk. También gratis.

### C) RDP nativo (más técnico)
RDP = Remote Desktop Protocol (protocolo nativo de Windows).
Requiere habilitar "Escritorio Remoto" en Settings de Windows + abrir
puerto 3389 en router. Más setup.

**Mi recomendación: AnyDesk**. 5 minutos de setup y funcionamos.

---

## Flujo del lunes (paso a paso)

1. Prendes tu PC Windows.
2. Instalas **AnyDesk** y me pasas tu código.
3. Desde mi Mac me conecto a tu PC vía AnyDesk.
4. Clonamos este repo en tu PC:
   ```cmd
   git clone https://github.com/peku82/SAP_to_Data_Platform.git
   cd SAP_to_Data_Platform
   ```
5. En tu PC Windows abres **Chrome** o **Edge**, vas a
   https://sapb1tmx.com.mx/ y haces login JKKU006 / FI002.
6. Abres **Generador de Consultas** (Herramientas → Consultas →
   Generador de consultas).
7. Por cada archivo de `sql_queries/*.sql`:
   - Pegas el contenido en la caja SQL
   - Ejecutar (reloj / F5)
   - _Archivo → Exportar → MS Excel_
   - Guardar como `<TABLA>_20260421.xlsx` en Descargas
8. Sincronizamos los 18 .xlsx a mi Mac (por OneDrive / cloud / SFTP
   desde el repo).
9. Yo corro `python scripts/extract_phase1.py` en mi Mac.
10. Fase 1 terminada.

---

## Credenciales / secretos — NO están en el repo
Los passwords viven en `config/.env` que está en `.gitignore`.
Cuando clones en Windows:
```cmd
copy config\.env.example config\.env
```
Y editas con los valores reales (los tengo yo — te los paso en el
grupo WhatsApp o aquí mismo).

---

## Servicios automáticos ya corriendo (en mi Mac)

Estos corren en mi máquina y siguen activos independientemente del
Windows del lunes:

- **launchd `com.jkkpack.sap.reporter`** — cada 4h envía
  status_report.txt al grupo WhatsApp
- **launchd `com.jkkpack.sap.group-poller`** — cada 5 min lee mensajes
  del grupo Migración Odoo y detecta triggers

Si quieres replicar estos en Windows, usa Task Scheduler. Pero
probablemente no hace falta — yo los mantengo en mi Mac.

---

## Estructura del repo

```
SAP_to_Data_Platform/
├── HANDOFF.md               ← este archivo
├── README.md                ← resumen + arranque rápido
├── .gitignore
├── config/
│   ├── .env.example         ← plantilla (sin secretos)
│   └── tables.yaml          ← 18 tablas + PK + delta cols
├── data/
│   ├── drop/                ← aquí dejas los .xlsx exportados
│   ├── raw/ clean/ processed/ delta/
├── database/                ← PostgreSQL schema + dumps (Fase 4)
├── docs/
│   ├── architecture.txt
│   ├── usage_guide.txt
│   ├── manual_export_guide.txt
│   └── ti_request.txt
├── logs/                    ← status reports, watermarks, flags
├── scripts/
│   ├── extract_phase1.py    ← procesa data/drop/ → data/raw/
│   ├── validate_extraction.py
│   ├── sap_connection.py    ← 4 modos de conexión
│   ├── status_reporter.py   ← WhatsApp reports
│   ├── group_poller.py      ← detecta triggers en grupo
│   └── requirements.txt
└── sql_queries/
    └── (18 .sql, uno por tabla)
```

---

## Contactos del proyecto

- **Jose Kuri** — dueño JKK Pack, decision maker
- **Victor** — admin SAP B1 / IT externo, habilita permisos
- **Alonso** — integrante del grupo Migración Odoo
- **Claude** (yo) — el agente que opera el pipeline

Grupo WhatsApp oficial: _Migración Odoo_ (el bot de SOMAS ya está
adentro, JID `120363409108344557@g.us`).
