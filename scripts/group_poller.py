"""group_poller.py

Poleo el endpoint /api/whatsapp/group-messages de SOMAS buscando mensajes
nuevos del grupo Migración Odoo. Cuando detecta un "listo" de Víctor
(o similar), activa un flag que indica que ya se puede extraer SAP.

Diseño:
  - guarda el último timestamp visto en logs/group_poller_watermark.json
  - solo procesa mensajes con timestamp > watermark
  - si detecta un disparador ("listo", "ya", "autorizado"), escribe
    logs/victor_authorized.flag con la metadata
  - también genera un snapshot de los últimos mensajes para debug

Uso:
    python scripts/group_poller.py          # un ciclo
    python scripts/group_poller.py --tail   # imprime últimos 10 mensajes

Programado por launchd com.jkkpack.sap.group-poller cada 5 min.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
CONFIG_DIR = ROOT / "config"

try:
    from dotenv import load_dotenv
    import requests
except ImportError:
    print("Faltan deps: pip install python-dotenv requests", file=sys.stderr)
    sys.exit(2)

load_dotenv(CONFIG_DIR / ".env")

SOMAS_URL = os.environ.get("SOMAS_WHATSAPP_URL",
                           "https://somas.jkkpack.app/api/whatsapp/send")
# Derivamos la base reemplazando /send por /group-messages
SOMAS_BASE = SOMAS_URL.replace("/send", "")
GROUP_JID = "120363409108344557@g.us"  # Migración Odoo
SECRET = os.environ.get("SOMAS_INTER_APP_SECRET", "soma-academy-secret-2024")

WATERMARK_FILE = LOGS_DIR / "group_poller_watermark.json"
FLAG_FILE = LOGS_DIR / "victor_authorized.flag"
SNAPSHOT_FILE = LOGS_DIR / "group_last_messages.json"

# Palabras que indican autorización (normalizadas a minúsculas y sin acentos)
TRIGGERS = ["listo", "autorizado", "ya quedo", "ya quedó", "ya esta", "ya está",
            "habilitado", "done"]


def _load_watermark() -> int:
    if not WATERMARK_FILE.exists():
        return 0
    try:
        return int(json.loads(WATERMARK_FILE.read_text()).get("timestamp", 0))
    except Exception:
        return 0


def _save_watermark(ts: int) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    WATERMARK_FILE.write_text(json.dumps({"timestamp": ts}))


def _normalize(s: str) -> str:
    s = s.lower().strip()
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s)


def _is_trigger(text: str) -> bool:
    n = _normalize(text)
    if len(n) > 100:
        return False
    for t in TRIGGERS:
        if t in n:
            return True
    return False


def fetch_messages(since_ts: int = 0, limit: int = 100) -> list[dict]:
    url = f"{SOMAS_BASE}/group-messages"
    params = {"jid": GROUP_JID, "limit": str(limit)}
    if since_ts:
        params["since"] = str(since_ts)
    r = requests.get(url, params=params, headers={
        "x-inter-app-secret": SECRET,
    }, timeout=15)
    r.raise_for_status()
    return r.json().get("messages", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", action="store_true",
                    help="Imprime los últimos 10 mensajes del grupo y sale")
    ap.add_argument("--reset", action="store_true",
                    help="Borra watermark y flag (reset)")
    args = ap.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if args.reset:
        for f in [WATERMARK_FILE, FLAG_FILE]:
            if f.exists():
                f.unlink()
        print("reset OK")
        return 0

    if args.tail:
        msgs = fetch_messages(limit=10)
        for m in msgs:
            when = dt.datetime.fromtimestamp(m["timestamp"] / 1000).strftime("%H:%M:%S")
            print(f"[{when}] {m.get('fromName') or '?'}: {m.get('text','')}")
        return 0

    watermark = _load_watermark()
    try:
        msgs = fetch_messages(since_ts=watermark)
    except Exception as e:
        print(f"error fetch: {e}", file=sys.stderr)
        return 1

    if not msgs:
        print("sin mensajes nuevos")
        return 0

    SNAPSHOT_FILE.write_text(json.dumps(msgs, ensure_ascii=False, indent=2))

    triggered = []
    max_ts = watermark
    for m in msgs:
        ts = m.get("timestamp", 0)
        if ts > max_ts:
            max_ts = ts
        txt = m.get("text", "")
        if _is_trigger(txt):
            triggered.append(m)

    _save_watermark(max_ts)

    if triggered:
        FLAG_FILE.write_text(json.dumps({
            "detected_at": dt.datetime.now().isoformat(timespec="seconds"),
            "message": triggered[-1],
            "reason": "palabra clave de autorización detectada",
        }, ensure_ascii=False, indent=2))
        print(f"TRIGGER DETECTADO. Mensaje: {triggered[-1].get('text')}")
        # Opcional: ping WhatsApp al grupo confirmando recepción
        try:
            requests.post(SOMAS_URL, json={
                "secret": SECRET,
                "phone": GROUP_JID,
                "message": f"Recibido \"{triggered[-1].get('text')}\". Arranco extracción SAP ahora.",
            }, timeout=10)
        except Exception:
            pass
        return 0

    print(f"{len(msgs)} mensajes nuevos, ningún trigger detectado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
