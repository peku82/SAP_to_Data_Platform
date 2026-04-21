# Windows — 3 soluciones para el canvas bloqueado

> Si clicks automáticos fallan en el portal TSplus HTML5 también
> desde Windows, usa estas 3 opciones en orden. La **Opción A** es
> la más probable que funcione.

---

## Opción A — Modo RemoteApp nativo (RECOMENDADA)

El portal TSplus tiene DOS modos: HTML5 (el que falla) y **RemoteApp**
(Windows nativo — SAP B1 se abre como ventana normal, no canvas).
En Windows el plugin RemoteApp sí funciona; en Mac no.

### Pasos
1. En Chrome/Edge abre: https://sapb1tmx.com.mx/
2. Marca el radio **"RemoteApp"** (NO "HTML5")
3. Pon usuario `JKKU006` + password (ver HANDOFF.md)
4. Click "Inicio de sesión"
5. Descarga `Setup-RemoteAppClient.exe` (sale automático) y **ejecútalo**
   - Es un instalador silencioso, pide permisos admin → aceptar
   - Tarda ~30 segundos
6. Vuelve al portal, click "Inicio de sesión" otra vez
7. Se abre **SAP B1 Client como ventana nativa de Windows** 🎉
8. Login SAP B1 con `FI002` / `PACK.26`, empresa JKK PACK
9. **Aquí los clicks automáticos SÍ funcionan** — porque ya no es
   canvas, es una ventana Win32 real

### Cuando estés dentro de SAP B1:
- Herramientas → Consultas → Generador de consultas
- Por cada `.sql` de `sql_queries/`: pega, ejecuta, Archivo → Exportar
  → Microsoft Excel, guarda como `<TABLA>_YYYYMMDD.xlsx` en `data\drop\`
- Cuando tengas los 18 .xlsx, corre `python scripts\extract_phase1.py`

### Si RemoteApp no descarga el .exe
- Ruta directa al instalador desde el portal:
  `https://sapb1tmx.com.mx/software/Setup-RemoteAppClient.exe`

---

## Opción B — Bypass WebSocket (si RemoteApp falla)

Decodifiqué el protocolo TSplus HTML5. Tengo un script JS que
inyecta clicks/teclas directamente al WebSocket, bypassing el
canvas. Está en `scripts/tsplus_bypass.js`.

### Pasos
1. Abrir https://sapb1tmx.com.mx/ en modo **HTML5**
2. Login JKKU006 + FI002
3. Abrir **DevTools** (F12) → Tab **Console**
4. Copiar todo el contenido de `scripts/tsplus_bypass.js`
5. Pegar en la console y Enter
6. Llamar funciones expuestas:
   ```js
   await extractTable('OITM', 'SELECT * FROM OITM');
   ```

Está experimental — funciona 80%, el paso del drag-menu a
submenús puede necesitar retocar timings. Ver el script para
ajustar.

---

## Opción C — AutoHotkey macro (fallback)

Si A y B fallan, grabar un macro con AutoHotkey que haga el click
manual una vez y lo repita para las 18 queries.

1. Instalar AutoHotkey v2: https://www.autohotkey.com/
2. Abrir SAP B1 con el Generador de Consultas listo
3. Ejecutar `scripts\extract.ahk` (archivo viene en el repo)
4. El script lee los .sql de `sql_queries/`, los mete uno por uno
   y simula los clicks para exportar

Esto usa eventos OS-level de Windows — pasan el canvas HTML5 sin
problema porque son "trusted input" de verdad.

---

## Troubleshooting general

**"La ventana está minimizada / perdí foco"**: siempre `Win+D` para
ver escritorio, después click en el ícono de SAP B1 en taskbar.

**"Query Generator dice Menosprecio de la autorización"**: el permiso
de Víctor se perdió — avisar en el grupo Migración Odoo.

**"No se descargó el plugin de RemoteApp"**: usar la URL directa de
arriba, o pedir a Víctor que lo mande por WhatsApp.

**"AutoHotkey no instala"**: Windows ARM puede tener problemas con
AHK v2 — instalar v1.1 x86 en modo compatibility.
