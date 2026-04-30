# PHASE 1 COMPLETA — handoff para nueva sesión

> Si abres esta conversación con un Claude nuevo, lee esto primero.
> Aquí está exactamente dónde quedamos al cerrar la sesión anterior
> y por dónde retomar.

---

## TL;DR del estado

- **Fecha de cierre Fase 1:** 2026-04-29
- **Status:** 🟢 Fase 1 completa, datos en disco listos para Fase 2
- **Quien hizo el export manual:** Víctor (IT externo de JKK Pack), desde
  su PC Windows con SAP B1 client nativo. Mandó zip por OneDrive
  corporativo de JKK.
- **Quien ya NO se necesita en flujo automático:** Víctor — los deltas
  semanales se manejarán por otro mecanismo (a definir en Fase 5).

---

## Qué tenemos en disco AHORA

### Archivos crudos en `data/drop/`
18 archivos `.xlsx` (originales que mandó Víctor):
```
INV1_20260429.xlsx   ITM1_20260429.xlsx   JDT1_20260429.xlsx
OACT_20260429.xlsx   OBTN_20260429.xlsx   OBTQ_20260429.xlsx
OCRD_20260429.xlsx   OINV_20260429.xlsx   OITB_20260429.xlsx
OITM_20260429.xlsx   OITW_20260429.xlsx   OJDT_20260429.xlsx
OPCH_20260429.xlsx   OPOR_20260429.xlsx   ORDR_20260429.xlsx
PCH1_20260429.xlsx   POR1_20260429.xlsx   RDR1_20260429.xlsx
```

### Archivos procesados en `data/raw/`
Mismo nombre pero `.csv` (UTF-8 con BOM, separador coma, quote ALL):
- 18 CSVs, ~950 MB total
- Generados por `python scripts/extract_phase1.py`

### Conteos confirmados (CSV ↔ SAP coincide 100%)

| Tabla | Filas | Tamaño CSV |
|-------|------:|-----------:|
| OBTQ  | 1,048,575 |  76 MB |
| OBTN  |   601,095 | 194 MB |
| JDT1  |   338,039 | 250 MB |
| OJDT  |   267,455 | 145 MB |
| OITW  |   195,279 |  56 MB |
| ITM1  |   114,850 |   9 MB |
| OITM  |    11,487 |  16 MB |
| OCRD  |     1,077 | 1.8 MB |
| OINV  |    11,853 |  50 MB |
| INV1  |    13,925 |  24 MB |
| OPCH  |    14,166 |  32 MB |
| PCH1  |    24,671 |  37 MB |
| ORDR  |     5,341 |  12 MB |
| RDR1  |     8,693 |  14 MB |
| OPOR  |     5,971 |  14 MB |
| POR1  |    11,936 |  19 MB |
| OACT  |       640 | 0.3 MB |
| OITB  |        42 | 24 KB  |
| **TOTAL** | **2,675,095** | **~950 MB** |

### Reporte de extracción
`logs/extract_20260429.json` — JSON con duración, columnas, status por tabla.

---

## ⚠️ Bug conocido del validador (no bloquea Fase 2)

`scripts/validate_extraction.py` reporta falsos positivos en `pk_duplicates`
porque busca PKs por nombre técnico en inglés (`CardCode`, `ItemCode`,
`DocEntry`...) pero los CSVs que mandó Víctor tienen headers traducidos al
español del módulo SAP B1 (ej. `Código SN`, `Número de artículo`,
`Número de documento`).

**Conteos de fila están correctos** (diff=0 en todas las 18 tablas).
Solo la lógica de detección de duplicados de PK está rota.

### Fix planeado (al arrancar Fase 2)
Crear `config/header_mapping.yaml` con el mapeo `header_es → snake_case_canonico`
y aplicarlo en `clean_phase2.py`. El validador reusa ese mapeo y los
falsos positivos desaparecen.

Headers reales detectados (parcial):
```
OCRD: "Código SN", "Nombre SN", "Clase de socio de negocios", ...
OITM: "Número de artículo", "Descripción del artículo", "Grupo de artículos", ...
```

---

## Repo GitHub

- URL: https://github.com/peku82/SAP_to_Data_Platform
- Visibilidad: **público**
- Último commit relevante: HANDOFF.md + WINDOWS_FIX.md + tsplus_bypass.js
  + extract.ahk (estos últimos 3 son obsoletos ya que Víctor lo hizo
  manual desde Windows nativo).

---

## Servicios automáticos en el Mac de Jose

Los launchd siguen corriendo. Si quieres apagarlos:
```bash
launchctl unload ~/Library/LaunchAgents/com.jkkpack.sap.reporter.plist
launchctl unload ~/Library/LaunchAgents/com.jkkpack.sap.group-poller.plist
```

Status actual:
- `com.jkkpack.sap.reporter` → status report cada 4h al grupo (silenciado
  en el código, no manda mensajes hasta que reactiven)
- `com.jkkpack.sap.group-poller` → poleo del grupo Migración Odoo cada
  5 min (sigue activo, no afecta nada)

---

## Próximos pasos (Fase 2)

Cuando el usuario diga "arranca Fase 2":

1. **Crear `config/header_mapping.yaml`** con mapeo headers ES → snake_case
   - Inspeccionar primeras filas de cada CSV en `data/raw/` para extraer
     los headers reales.
   - Convertir a snake_case canonico (ej. `Código SN` → `card_code`).

2. **Crear `scripts/clean_phase2.py`** que:
   - Lee `data/raw/<TABLA>_<fecha>.csv`
   - Renombra columnas usando el mapping
   - Elimina duplicados exactos
   - Normaliza textos (trim, casing donde aplique)
   - Homologa unidades de medida
   - Detecta nulos críticos
   - Escribe `data/clean/<TABLA>_<fecha>.csv`
   - Genera `<TABLA>_<fecha>_quality.json` con reporte de calidad.

3. **Arreglar `validate_extraction.py`** para usar el mapping ES → snake_case
   en la búsqueda de PKs.

4. Después: Fase 3 (estructuración + FKs), Fase 4 (PostgreSQL).

---

## Cómo el deltas funcionarán (Fase 5+, plan)

Como NO podemos automatizar la extracción desde Mac (limitación canvas
TSplus + AnyDesk + focus de teclado — bien documentado en HANDOFF.md),
el modelo de deltas será:

- **Opción A:** Víctor recibe cada lunes un mensaje WhatsApp automático
  desde nuestro pipeline pidiéndole que ejecute solo las queries delta
  (con filtro `UpdateDate >= <último_watermark>`) y suba el zip a la
  misma carpeta OneDrive. Nuestro pipeline poleo OneDrive.

- **Opción B:** PowerShell script en su PC Windows que corra programado
  los lunes y suba auto a OneDrive (Víctor no tiene que hacer nada
  manual). Lo escribimos cuando arranquemos Fase 5.

---

## Contactos del proyecto

- **Jose Kuri** — dueño JKK Pack
- **Víctor** — admin SAP B1 / IT, hizo el export Fase 1
- **Alonso** — integrante grupo Migración Odoo
- **Grupo WhatsApp:** Migración Odoo
  (JID `120363409108344557@g.us`)
- **Bot SOMAS WhatsApp:** https://somas.jkkpack.app
  (secret `soma-academy-secret-2024`, header `x-inter-app-secret`)

---

## Para Claude nuevo

1. Lee este archivo + `HANDOFF.md` + `README.md` antes de actuar.
2. **No reintentes la automatización TSplus desde Mac** — está documentado
   por qué no funciona (canvas streaming + focus issues). Víctor ya hizo
   la extracción manual una vez, eso queda como modelo para deltas.
3. Si Jose dice "arranca Fase 2", ejecuta el plan de "Próximos pasos"
   arriba.
4. Si dice "carga a PostgreSQL", salta a Fase 4 directo (el clean de
   Fase 2 puede hacerse en SQL después).
5. Para reportar al grupo WhatsApp, usar `scripts/status_reporter.py`
   o curl directo al endpoint de SOMAS.
