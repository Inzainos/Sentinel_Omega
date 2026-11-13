#!/usr/bin/env python3
"""
Backfill Schumann daily cut for missing days.

Acumula días faltantes en tbl_schumann_diario (actividad IS NULL o fuente='tomsk_fallido')
y los procesa cuando Tomsk vuelve a responder.

Uso:
  python scripts/backfill_schumann_missing.py --desde 2026-11-01 --hasta hoy

El script:
  1. Lee la lista de días faltantes.
  2. Guarda el acumulado en estado/missing_schumann_days.txt
  3. Para cada día, intenta un corte diario con `ahora` apuntando al mediodía del día
     objetivo. El corte diario mantiene la regla de 1 descarga/día: si el día ya está
     marcado como fallido, no reintenta hasta el siguiente día real.
  4. Si Tomsk está caído, deja el día como pendiente y continúa con el siguiente
     ciclo; no genera 288 intentos/día.

Nota: el fetcher de Tomsk solo sirve imagen en vivo. Para recuperar histórico real
se requiere un archivo externo (p.ej. schumannresonance.today/archive). Este
script acumula los días y deja la cola lista para un backfill con fuente externa
cuando se integre.
"""

import argparse
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parents[1] / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"
ESTADO_DIR = Path(__file__).resolve().parents[1] / "estado"
MISSING_FILE = ESTADO_DIR / "missing_schumann_days.txt"

def get_missing_days(conn, start, end):
    cur = conn.execute(
        "SELECT fecha FROM tbl_schumann_diario WHERE fecha BETWEEN ? AND ? AND (actividad IS NULL OR fuente = 'tomsk_fallido') ORDER BY fecha",
        (start, end)
    )
    return [r[0] for r in cur.fetchall()]

def accumulate_missing(start, end):
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    missing = get_missing_days(conn, start, end)
    conn.close()

    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    with open(MISSING_FILE, "w") as f:
        for d in missing:
            f.write(d + "\n")
    log.info("Días faltantes acumulados: %d -> %s", len(missing), MISSING_FILE)
    if missing:
        log.info("Primeros: %s", missing[:5])
        log.info("Últimos: %s", missing[-5:])
    return missing

def try_backfill_one_day(day_str):
    """Intenta corte diario para un día específico usando ahora apuntado al día."""
    from sentinel_omega.core.schumann_vivo import corte_diario
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    # Mediodía UTC del día objetivo
    dt = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    dt = dt.replace(hour=12, minute=0, second=0)
    ahora = dt.timestamp()
    try:
        res = corte_diario(conn, ahora=ahora)
        log.info("Backfill %s -> %s", day_str, res.get("estado"))
    except Exception as e:
        log.warning("Backfill %s falló: %s", day_str, e)
    finally:
        conn.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--desde", required=True, help="YYYY-MM-DD")
    p.add_argument("--hasta", default=None, help="YYYY-MM-DD, por defecto hoy")
    p.add_argument("--procesar", action="store_true", help="Intenta procesar la cola acumulada")
    args = p.parse_args()

    start = args.desde
    end = args.hasta or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    missing = accumulate_missing(start, end)

    if args.procesar:
        # Procesa solo el primer día pendiente para no romper la regla de 1 descarga/día
        # en vivo. Para backfill histórico real se necesita fuente externa.
        if missing:
            log.info("Procesando primer día pendiente: %s", missing[0])
            try_backfill_one_day(missing[0])
        else:
            log.info("No hay días pendientes")

if __name__ == "__main__":
    main()
