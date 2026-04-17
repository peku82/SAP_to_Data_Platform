"""status_reporter.py

Genera logs/status_report.txt y lo envía por WhatsApp al +52 1 55 2653 9904
a través del endpoint interno de SOMAS.

Uso:
    python scripts/status_reporter.py                 # genera + envía
    python scripts/status_reporter.py --no-send       # solo genera archivo
    python scripts/status_reporter.py --phase "Fase 2" --pct 40 \
        --done "Limpieza OITM,OCRD" --errors "ninguno" \
        --next "validar SKUs"                         # override manual

Si no hay overrides, el script infiere el estado leyendo:
    logs/extract_<latest>.json
    logs/validate_<latest>.json
    logs/errors.log
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
CONFIG_DIR = ROOT / "config"

try:
    from dotenv import load_dotenv
    import requests
except ImportError:
    print("Faltan dependencias: pip install python-dotenv requests", file=sys.stderr)
    sys.exit(2)

load_dotenv(CONFIG_DIR / ".env")


def _latest(pattern: str) -> Optional[Path]:
    matches = sorted(LOGS_DIR.glob(pattern))
    return matches[-1] if matches else None


def _infer_state() -> dict:
    """Construye un resumen leyendo los últimos reportes JSON."""
    state = {
        "phase": "Fase 1 — Extracción inicial",
        "pct": 0,
        "done": [],
        "in_progress": [],
        "errors": [],
        "next": [],
        "blockers": [],
        "detail": {},
    }

    extract = _latest("extract_*.json")
    validate = _latest("validate_*.json")

    # Heurística: infraestructura creada siempre. Sin extracción real aún.
    if not extract:
        state["pct"] = 35
        state["done"] = [
            "Estructura de carpetas creada",
            "18 consultas SQL listas en sql_queries/ para Query Manager",
            "Pipeline configurado en modo csv_drop (ingesta .xlsx/.csv)",
            "Guía del operador docs/manual_export_guide.txt",
            "Reportero WhatsApp configurado cada 4h",
        ]
        state["blockers"] = [
            "Acceso SAP es solo portal RemoteApp. No hay API ni DB abierta.",
            "Pendiente: operador con FI002 ejecuta las 18 consultas y "
            "exporta a Excel a data/drop/.",
        ]
        state["next"] = [
            "Operador entra a SAP B1 y corre las 18 queries (Query Manager)",
            "Deja los .xlsx en data/drop/ con nombre <TABLA>_<YYYYMMDD>.xlsx",
            "Correr: python scripts/extract_phase1.py",
            "Correr: python scripts/validate_extraction.py",
        ]
    else:
        with open(extract, "r", encoding="utf-8") as f:
            ex = json.load(f)
        ok = ex["totals"]["tables_ok"]
        fail = ex["totals"]["tables_failed"]
        rows = ex["totals"]["rows"]
        total = ok + fail
        pct = 40 if fail == 0 else int(40 * ok / max(total, 1))
        state["pct"] = pct
        state["done"].append(
            f"Extracción Fase 1: {ok}/{total} tablas, {rows:,} filas"
        )
        if fail:
            state["errors"].append(f"{fail} tablas fallaron en extracción")
        state["detail"]["extract"] = str(extract.name)

        if validate:
            with open(validate, "r", encoding="utf-8") as f:
                vd = json.load(f)
            err = vd.get("errors", 0)
            if err == 0:
                state["done"].append("Validación Fase 1: 0 errores")
                state["pct"] = 50
                state["next"] = ["Arrancar Fase 2 (limpieza)"]
            else:
                state["errors"].append(f"Validación: {err} inconsistencias")
                state["next"] = ["Revisar logs/validate_*.json antes de Fase 2"]
            state["detail"]["validate"] = str(validate.name)

    # errores globales
    errfile = LOGS_DIR / "errors.log"
    if errfile.exists() and errfile.stat().st_size > 0:
        state["errors"].append(f"Ver logs/errors.log ({errfile.stat().st_size} bytes)")

    return state


def _format_report(state: dict) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "================================================",
        " SAP → Data Platform — REPORTE DE AVANCE",
        "================================================",
        f" Generado:  {now}",
        f" Fase:      {state['phase']}",
        f" Avance:    {state['pct']}%",
        "",
        "-- Tareas completadas ---------------------------",
    ]
    lines.extend(f"  • {x}" for x in state["done"]) if state["done"] else lines.append("  (ninguna)")
    if state["in_progress"]:
        lines += ["", "-- En curso ------------------------------------"]
        lines.extend(f"  • {x}" for x in state["in_progress"])
    lines += ["", "-- Errores -------------------------------------"]
    lines.extend(f"  • {x}" for x in state["errors"]) if state["errors"] else lines.append("  ninguno")
    lines += ["", "-- Próximos pasos ------------------------------"]
    lines.extend(f"  • {x}" for x in state["next"]) if state["next"] else lines.append("  (definir)")
    lines += ["", "-- Bloqueos ------------------------------------"]
    lines.extend(f"  • {x}" for x in state["blockers"]) if state["blockers"] else lines.append("  ninguno")
    lines.append("================================================")
    return "\n".join(lines)


def _whatsapp_body(state: dict) -> str:
    now = dt.datetime.now().strftime("%d/%b %H:%M")
    parts = [
        f"*SAP → Data Platform*  ({now})",
        f"*Fase:* {state['phase']}  —  *{state['pct']}%*",
    ]
    if state["done"]:
        parts.append("\n*Hecho:*\n" + "\n".join(f"• {x}" for x in state["done"][:4]))
    if state["errors"]:
        parts.append("\n*Errores:*\n" + "\n".join(f"• {x}" for x in state["errors"][:3]))
    if state["blockers"]:
        parts.append("\n*Bloqueos:*\n" + "\n".join(f"• {x}" for x in state["blockers"][:3]))
    if state["next"]:
        parts.append("\n*Próximo:*\n" + "\n".join(f"• {x}" for x in state["next"][:3]))
    return "\n".join(parts)


def _send_whatsapp(message: str, logger=print) -> bool:
    url = os.environ.get("SOMAS_WHATSAPP_URL",
                         "https://somas.jkkpack.app/api/whatsapp/send")
    secret = os.environ.get("SOMAS_INTER_APP_SECRET",
                            "jkkpack-inter-app-2026")
    phone = os.environ.get("REPORT_WHATSAPP_NUMBER", "5215526539904")
    try:
        r = requests.post(url, json={
            "phone": phone, "message": message, "secret": secret,
        }, timeout=30)
        if r.status_code >= 400:
            logger(f"WhatsApp error HTTP {r.status_code}: {r.text[:300]}")
            return False
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if data.get("success") is False:
            logger(f"WhatsApp rechazado: {data.get('error')}")
            return False
        logger("WhatsApp enviado OK")
        return True
    except Exception as e:
        logger(f"WhatsApp falló: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase")
    ap.add_argument("--pct", type=int)
    ap.add_argument("--done")
    ap.add_argument("--errors")
    ap.add_argument("--next", dest="next_")
    ap.add_argument("--blockers")
    ap.add_argument("--no-send", action="store_true",
                    help="Solo genera archivo, no manda WhatsApp")
    args = ap.parse_args()

    state = _infer_state()
    if args.phase: state["phase"] = args.phase
    if args.pct is not None: state["pct"] = args.pct
    if args.done: state["done"] = [s.strip() for s in args.done.split(",") if s.strip()]
    if args.errors: state["errors"] = [s.strip() for s in args.errors.split(",") if s.strip()]
    if args.next_: state["next"] = [s.strip() for s in args.next_.split(",") if s.strip()]
    if args.blockers: state["blockers"] = [s.strip() for s in args.blockers.split(",") if s.strip()]

    report = _format_report(state)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out = LOGS_DIR / "status_report.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)

    # snapshot histórico
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    with open(LOGS_DIR / f"status_report_{stamp}.txt", "w", encoding="utf-8") as f:
        f.write(report)

    print(report)

    if not args.no_send:
        _send_whatsapp(_whatsapp_body(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
