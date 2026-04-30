# FASES 2, 3 y 4 COMPLETAS — handoff para nueva sesión

> Continuación de [PHASE1_COMPLETE.md](./PHASE1_COMPLETE.md). Si abres
> esta conversación con un Claude nuevo, lee primero el de Fase 1 y
> luego este.

---

## TL;DR del estado

- **Fecha de cierre Fase 4:** 2026-04-29
- **Status:** 🟢 Las 4 fases completas. Replica SAP B1 viva en PostgreSQL local.
- **Total filas en PG:** 2,675,095 (= SAP exacto, diff=0 en las 18 tablas)
- **Tamaño BD:** 867 MB en sap_replica (PostgreSQL 16 via brew)
- **Próximos pasos:** transformar a Odoo + diseñar pipeline de deltas (Fase 5).

---

## Lo que está corriendo ahora

### PostgreSQL local
```
brew services start postgresql@16
DSN: postgresql:///sap_replica   (socket local, user=josekuri)
psql: /opt/homebrew/opt/postgresql@16/bin/psql -h localhost -d sap_replica
```

### Schema y tablas
```
sap.ocrd  (Socios de negocio)         1,077  rows  · 405 cols · 1.4 MB
sap.oitm  (Articulos)                11,487  rows  · 348 cols · 10  MB
sap.oitb  (Grupos articulos)             42  rows  ·  82 cols · 104 KB
sap.itm1  (Listas precio)           114,850  rows  ·  18 cols · 13  MB
sap.oitw  (Stock por almacen)       195,279  rows  ·  76 cols · 45  MB
sap.obtn  (Lotes)                   601,095  rows  ·  39 cols · 204 MB
sap.obtq  (Saldos lote x almacen) 1,048,575  rows  ·  12 cols · 149 MB
sap.ordr  (Pedidos venta)             5,341  rows  · 530 cols · 8.0 MB
sap.rdr1  (Lineas pedidos venta)      8,693  rows  · 359 cols · 9.9 MB
sap.opor  (Pedidos compra)            5,971  rows  · 528 cols · 9.8 MB
sap.por1  (Lineas pedidos compra)    11,936  rows  · 357 cols · 12  MB
sap.oact  (Plan cuentas)                640  rows  · 131 cols · 488 KB
sap.ojdt  (Asientos contables)      267,455  rows  · 114 cols · 107 MB
sap.jdt1  (Lineas asientos)         338,039  rows  · 147 cols · 186 MB
sap.oinv  (Facturas venta)           11,853  rows  · 530 cols · 45  MB
sap.inv1  (Lineas facturas venta)    13,925  rows  · 360 cols · 16  MB
sap.opch  (Facturas compra)          14,166  rows  · 530 cols · 20  MB
sap.pch1  (Lineas facturas compra)   24,671  rows  · 357 cols · 23  MB
```

Cada tabla tiene:
- `PRIMARY KEY` sobre los PKs canonicos (snake_case).
- `INDEX` en `update_date`, `create_date`, `doc_date`, `ref_date` cuando
  existen (para deltas).
- Todas las columnas como TEXT (preserva fidelidad SAP). Las fechas
  watermark son TIMESTAMP.

---

## Decisiones de diseño clave

1. **Headers ES → snake_case canonico**
   `config/header_mapping.yaml` mapea cada header del export ES de Víctor
   a un nombre snake_case. Los PKs y FKs usan los nombres canonicos SAP
   (`card_code`, `item_code`, `doc_entry`, `line_num`, `trans_id`,
   `line_id`, `acct_code`, etc.). Watermarks unificados como
   `update_date` / `create_date`.

2. **No hay FOREIGN KEYS**
   Fase 3 detectó **332 huérfanos** en relaciones implícitas — clientes
   y proveedores históricos borrados en SAP B1 cuyos documentos siguen
   apareciendo. La carga es **soft-FK**: dejamos que esos registros
   queden en PG sin enforcement, y al transformar a Odoo decidimos
   caso-por-caso (`fk_set_null`, `fk_create_orphan_partner`, etc.).

3. **Todo TEXT excepto fechas watermark**
   Los exports ES de SAP B1 mezclan separadores numéricos europeos y
   formatos heterogéneos (`1.234,56` y `1234.56` aparecen ambos). En vez
   de adivinar tipos al cargar, persistimos todo como TEXT y casteamos
   en queries / al transformar a Odoo. Más lento por query, pero
   100% fiel y sin perder data.

4. **Quirk LineNum=0 → ""**
   SAP exporta la primera línea de cada doc con `LineNum`/`Line_ID`
   vacío. Phase 2 sustituye `""` por `"0"` en estas columnas para
   restaurar el PK. Sin este fix había 142,084 PKs nulos (5 tablas).

---

## Cómo correr todo el pipeline

```bash
cd ~/claude/SAP_to_Data_Platform
source .venv/bin/activate

# Si los CSVs raw existen en data/raw/:
python scripts/build_header_mapping.py     # genera config/header_mapping.yaml
python scripts/clean_phase2.py             # raw -> clean (snake_case, dedupe)
python scripts/validate_extraction.py      # valida vs expected_counts.yaml
python scripts/structure_phase3.py         # valida FKs implicitas
python scripts/load_phase4.py              # carga a PostgreSQL
```

Tiempos en el Mac Studio M-series (referencia):
- Phase 2 (clean):     ~3 segundos (polars streaming)
- Phase 3 (structure): ~0.3 segundos
- Phase 4 (load PG):   ~17 segundos
- **Total end-to-end:  ~20 segundos** para 2.6M filas

---

## Reportes generados

```
logs/clean_20260429.json         · resumen Fase 2 (filas, dups, nulls por tabla)
logs/quality/<TABLA>_*_quality.json · detalle por tabla (top null cols, etc.)
logs/structure_20260429.json     · 19 reglas FK + huerfanos detectados
logs/load_20260429.json          · resumen Fase 4 (filas en PG vs SAP)
logs/validate_20260429.{json,log} · validacion vs expected_counts.yaml
```

---

## Pipeline de deltas (Fase 5, plan)

El usuario lo va a tener que mantener actualizado **hasta el día de
go-live a Odoo**, así que el pipeline de deltas es lo siguiente:

### Inputs
- Víctor manda zip OneDrive cada lunes con CSVs filtrados por
  `UpdateDate >= <último_watermark>` (las queries delta están en
  `sql_queries/`).
- O bien: PowerShell programado en su PC sube auto a OneDrive.

### Mecánica del delta apply
1. `data/drop/<TABLA>_<fecha>.csv` ← snapshot delta nuevo
2. `python scripts/clean_phase2.py --tables <T1> <T2>` para limpiar solo los cambiados
3. `python scripts/structure_phase3.py` para volver a verificar FKs (deltas pueden romper)
4. **UPSERT** en lugar de DROP+CREATE en Phase 4. Reescribir
   `load_phase4.py` con dos modos:
   - `--mode initial`  (lo que tenemos hoy: drop + copy)
   - `--mode delta`    (INSERT ... ON CONFLICT (pk) DO UPDATE)
5. Actualizar `config/expected_counts.yaml` con los nuevos totales.
6. `psql -c "REFRESH MATERIALIZED VIEW ..."` si agregamos vistas.

### Watermarks tras la carga inicial
```
sap.ocrd.update_date   max = 2026-04-28
sap.oitm.update_date   max = 2026-04-28
sap.oinv.update_date   max = 2026-04-28
sap.opch.update_date   max = 2026-04-29
sap.ordr.update_date   max = 2026-04-28
```
La query delta para Víctor sería: `WHERE UpdateDate >= '2026-04-28'`.

---

## Cómo movernos de local a DigitalOcean (cuando toque)

Hoy PG está local en el Mac. Cuando se quiera compartir con el equipo
o conectar Odoo:

```bash
# 1. dump local
/opt/homebrew/opt/postgresql@16/bin/pg_dump -h localhost -d sap_replica -Fc -f sap_replica.dump

# 2. provisionar managed PG en DO  (o droplet con postgres)
# 3. restore
pg_restore -h db-do.jkkpack.app -U sap_replica -d sap_replica sap_replica.dump

# 4. cambiar PG_DSN en .env y rerun load_phase4.py si se quiere recargar
```

---

## Próximos pasos sugeridos para Fase 5+

1. **Vistas semánticas** — crear `sap_v.partners`, `sap_v.products`,
   `sap_v.invoices` con columnas casteadas y nombres en inglés/español
   estables. Aísla a Odoo de cambios en el schema raw.

2. **Mapeo a Odoo** — empezar con `res.partner` (desde `sap.ocrd` +
   direcciones desde `sap.crd1` cuando se exporte) y `product.product`
   (desde `sap.oitm`). Generar SQL→CSV→`odoo-import` o usar
   `odoo-shell`.

3. **CRD1 / OUSR / OPRC y otras tablas que faltan** — cuando se
   quiera traer direcciones de SN, usuarios, lista de precios extra,
   etc., agregar a `config/tables.yaml`, pedir a Víctor el export, y
   correr el pipeline.

4. **Mantener `expected_counts.yaml` vivo** — en cada delta apply,
   actualizar los conteos para que `validate_extraction.py` siga
   detectando regresiones.

---

## Para Claude nuevo

1. Lee `PHASE1_COMPLETE.md` + este archivo + `HANDOFF.md`.
2. Verifica que Postgres esté corriendo:
   `brew services list | grep postgres`
3. Para tocar PG: `psql -h localhost -d sap_replica`.
4. Para re-correr el pipeline tras un nuevo drop de Víctor:
   - reemplaza `data/raw/*.csv`
   - opcionalmente actualiza `config/expected_counts.yaml`
   - corre `python scripts/clean_phase2.py && python scripts/load_phase4.py`
5. **No reintentes la automatización TSplus** — sigue documentado por qué no funciona.
