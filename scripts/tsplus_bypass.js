/**
 * tsplus_bypass.js
 *
 * Bypass de canvas HTML5 del portal TSplus.
 * Inyecta clicks/teclas directamente al WebSocket del cliente
 * RemoteApp sin pasar por el canvas.
 *
 * USO:
 *   1. Abrir https://sapb1tmx.com.mx/ en modo HTML5
 *   2. Login JKKU006 + FI002
 *   3. F12 → Console → pegar TODO este archivo → Enter
 *   4. Llamar funciones:
 *        await openQueryGenerator();
 *        await runQuery('SELECT * FROM OITM');
 *        await exportToExcel('OITM_20260421.xlsx');
 *
 * DEPENDE DE:
 *   - objeto `W` global (cliente TSplus HTML5 — expuesto por portal)
 *   - WebSocket del cliente (se hookea automáticamente)
 *
 * PROTOCOLO TSplus decodificado:
 *   formato:    \x1c m \x1d <seq> \x1e M \x1f <payload>
 *   teclado:    !.!KEY = down, :.:KEY = up, !.2KEY = down+up
 *   mouse:      *m<X>x<Y> = move, =.=dwn, = down, =.=up, = up, =.=dwn,up, = click
 *   delimitador:.d. (inicio/fin de secuencia)
 */

(() => {
  'use strict';

  // -----------------------------------------------------
  // 1. Hook WebSocket para capturar el socket activo
  // -----------------------------------------------------
  if (!window.__tsbypass) {
    window.__tsbypass = {
      wsRef: null,
      seqMap: {
        click: 7, move: 7, down: 7, up: 6,
        key: 5, esc: 9, enter: 8, delim: 3,
      },
      SCALE: null,
    };
    const origSend = WebSocket.prototype.send;
    WebSocket.prototype.send = function (data) {
      window.__tsbypass.wsRef = this;
      return origSend.apply(this, arguments);
    };

    // Disparar un sendDU(F2) mudo para capturar el WS sin efecto visible
    if (typeof W !== 'undefined' && W.sendDU) {
      W.sendDU('');  // noop que sí triggerea WebSocket
    }
  }

  // -----------------------------------------------------
  // 2. Detectar escala del canvas (viewport/screenshot)
  // -----------------------------------------------------
  (() => {
    const canvas = document.querySelector('canvas');
    const rect = canvas.getBoundingClientRect();
    // En TSplus, las coords que el servidor recibe son escaladas según DPR
    const dpr = window.devicePixelRatio || 1;
    // El viewport canvas.width es el "real" del servidor
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    window.__tsbypass.SCALE = { x: scaleX, y: scaleY, dpr };
    console.log('[tsbypass] canvas=' + canvas.width + 'x' + canvas.height +
                ' rect=' + Math.round(rect.width) + 'x' + Math.round(rect.height) +
                ' scale=' + scaleX.toFixed(2) + 'x' + scaleY.toFixed(2));
  })();

  // -----------------------------------------------------
  // 3. Helpers de envío WebSocket
  // -----------------------------------------------------
  const msg = (seq, payload) => '\x1cm\x1d' + seq + '\x1eM\x1f' + payload;
  const send = (seq, payload) => {
    const ws = window.__tsbypass.wsRef;
    if (!ws) throw new Error('WebSocket no capturado todavía. Ejecuta W.sendDU("") primero.');
    ws.send(msg(seq, payload));
  };

  const toServer = (x, y) => {
    const s = window.__tsbypass.SCALE;
    return [Math.round(x * s.x), Math.round(y * s.y)];
  };

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // -----------------------------------------------------
  // 4. Funciones públicas expuestas en window
  // -----------------------------------------------------
  window.tsClick = (cssX, cssY) => {
    const [sx, sy] = toServer(cssX, cssY);
    const m = window.__tsbypass.seqMap;
    send(m.delim, '.d.');
    send(m.move, '*m' + sx + 'x' + sy);
    send(m.click, '=.=dwn,up,');
    send(m.delim, '.d.');
  };

  window.tsMouseDown = (cssX, cssY) => {
    const [sx, sy] = toServer(cssX, cssY);
    const m = window.__tsbypass.seqMap;
    send(m.delim, '.d.');
    send(m.move, '*m' + sx + 'x' + sy);
    send(m.down, '=.=dwn,');
  };

  window.tsMouseUp = (cssX, cssY) => {
    const [sx, sy] = toServer(cssX, cssY);
    const m = window.__tsbypass.seqMap;
    send(m.move, '*m' + sx + 'x' + sy);
    send(m.up, '=.=up,');
    send(m.delim, '.d.');
  };

  window.tsMove = (cssX, cssY) => {
    const [sx, sy] = toServer(cssX, cssY);
    const m = window.__tsbypass.seqMap;
    send(m.move, '*m' + sx + 'x' + sy);
  };

  window.tsKey = (keyName) => {
    // keyName: "F1", "Enter", "Escape", "Down", "Right", "Tab", letras...
    const m = window.__tsbypass.seqMap;
    send(m.key, '!.2' + keyName);
  };

  window.tsType = async (text, perCharDelay = 40) => {
    for (const ch of text) {
      window.tsKey(ch);
      await sleep(perCharDelay);
    }
  };

  /**
   * Drag menu: clickDown en origen, pasa por puntos intermedios, clickUp
   * en destino. Esto navega submenús de SAP sin que se cierren.
   */
  window.tsDragMenu = async (points, stepDelay = 400) => {
    const [x0, y0] = points[0];
    window.tsMouseDown(x0, y0);
    await sleep(200);
    for (let i = 1; i < points.length; i++) {
      const [x, y] = points[i];
      window.tsMove(x, y);
      await sleep(stepDelay);
    }
    const [xN, yN] = points[points.length - 1];
    window.tsMouseUp(xN, yN);
  };

  // -----------------------------------------------------
  // 5. Flujos de alto nivel para extracción
  // -----------------------------------------------------

  /**
   * Abre Herramientas → Consultas → Generador de consultas.
   * NOTA: las coordenadas son aproximadas, calibrar con
   *   tsClick(x, y) manualmente y ajustar si no abre.
   */
  window.openQueryGenerator = async () => {
    // Click menú Herramientas (posición aprox 187,7 en CSS px)
    window.tsClick(187, 7);
    await sleep(500);
    // Click "Consultas" (aprox 195, 113)
    window.tsClick(195, 113);
    await sleep(500);
    // Click "Generador de consultas" (aprox 425, 122)
    window.tsClick(425, 122);
    await sleep(1000);
  };

  /**
   * Escribe SQL en el Generador y ejecuta con F5.
   * Asume que el Generador ya está abierto y el campo "Seleccionar"
   * es el que toma foco por default.
   */
  window.runQuery = async (sqlText) => {
    // Click en el textarea del Generador (posición aprox)
    // Calibra con la captura — para SAP B1 en TSplus el editor suele
    // estar en ~500,190 del canvas
    window.tsClick(500, 190);
    await sleep(300);
    await window.tsType(sqlText, 20);
    await sleep(300);
    // F5 ejecuta la consulta
    window.tsKey('F5');
    await sleep(2000);
  };

  /**
   * Archivo → Exportar → Microsoft Excel usando DRAG MENU.
   * Las coords son tentativas — medir con screenshot real.
   * PUNTOS del drag:
   *   (15, 7)    click inicial en "Archivo"
   *   (35, 105)  baja a "Exportar" (se abre submenu)
   *   (100, 110) entra al submenu horizontalmente
   *   (178, 151) click final en "MS Excel"
   */
  window.exportToExcel = async () => {
    await window.tsDragMenu([
      [15, 7],
      [15, 50],
      [35, 105],
      [100, 110],
      [178, 151],
    ], 400);
    await sleep(2000);
  };

  /**
   * Flujo completo para una tabla:
   *   abre Generador → escribe SQL → ejecuta → exporta Excel
   */
  window.extractTable = async (tableName, sqlText) => {
    console.log('[tsbypass] extrayendo ' + tableName + '...');
    await window.openQueryGenerator();
    await window.runQuery(sqlText);
    await window.exportToExcel();
    console.log('[tsbypass] ' + tableName + ' hecho');
  };

  console.log('[tsbypass] cargado. Funciones disponibles:');
  console.log('  tsClick(x, y)');
  console.log('  tsMouseDown/tsMouseUp/tsMove(x, y)');
  console.log('  tsKey(keyName)   tsType(text)');
  console.log('  tsDragMenu([[x,y], ...], delayMs)');
  console.log('  openQueryGenerator()');
  console.log('  runQuery(sqlText)');
  console.log('  exportToExcel()');
  console.log('  extractTable(nombre, sql)');
  console.log('');
  console.log('Pruébalo: await tsClick(187, 7)  // debe abrir menú Herramientas');
})();
