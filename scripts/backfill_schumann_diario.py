#!/usr/bin/env python3
"""
Backfill script for missing Schumann daily records.

Identifies gaps in tbl_schumann_diario and fills them using:
- ResonanceOne API for current/recent days
- Historical data where available
- Marks gaps that cannot be filled automatically

Usage:
  python scripts/backfill_schumann_diario.py [--desde YYYY-MM-DD] [--hasta YYYY-MM-DD] [--dry-run]
"""

import argparse
import logging
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sentinel_omega"))

from sentinel_omega.core.schumann_vivo import asegurar_diario
from sentinel_omega.infrastructure.api.schumann_fallback import fetch_resonanceone

DB_PATH = Path(__file__).resolve().parents[1] / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BACKFILL] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_existing_dates(conn, start_date, end_date):
    """Get existing dates in tbl_schumann_diario within range."""
    rows = conn.execute(
        "SELECT fecha FROM tbl_schumann_diario WHERE fecha BETWEEN ? AND ?",
        (start_date, end_date)
    ).fetchall()
    return {r[0] for r in rows}


def find_missing_dates(start_str, end_str):
    """Find all dates in range that don't have a record."""
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    
    all_dates = set()
    current = start
    while current <= end:
        all_dates.add(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    conn = sqlite3.connect(str(DB_PATH))
    try:
        existing = get_existing_dates(conn, start_str, end_str)
    finally:
        conn.close()
    
    missing = sorted(all_dates - existing)
    return missing


def backfill_from_resonanceone(conn, date_str, dry_run=False):
    """Try to backfill a date using ResonanceOne API.
    
    Note: ResonanceOne API only returns current data, not historical.
    This will only work for today or very recent days if the API
    supports historical queries (it doesn't currently).
    
    Returns True if backfilled, False otherwise.
    """
    # ResonanceOne /api/now only returns current reading
    # For historical backfill we'd need /api/history which doesn't exist
    # So we can only fill today or accept we can't fill historical gaps
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if date_str != today:
        logger.debug(f"ResonanceOne no proporciona histórico para {date_str} (solo {today})")
        return False
    
    fb = fetch_resonanceone()
    if not fb:
        logger.warning(f"ResonanceOne no disponible para {date_str}")
        return False
    
    freq, act, fuente, meta = fb
    
    if dry_run:
        logger.info(f"[DRY RUN] Backfill {date_str}: actividad={act:.2f}%, fuente={fuente}, calidad={meta.get('calidad')}")
        return True
    
    asegurar_diario(conn)
    conn.execute(
        "INSERT OR REPLACE INTO tbl_schumann_diario "
        "(fecha, actividad, actividad_raw, frecuencia_hz, fuente, calidad, confianza, sesgo_aplicado) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (date_str, act, meta.get("schumann_index_raw"), freq, fuente,
         meta.get("calidad"), meta.get("confidence_score"), meta.get("calibration_factor")),
    )
    conn.commit()
    logger.info(f"Backfill {date_str}: actividad={act:.2f}%, fuente={fuente}, calidad={meta.get('calidad')}")
    return True


def mark_gap(conn, date_str, dry_run=False):
    """Mark a date as a known gap (no data available)."""
    if dry_run:
        logger.info(f"[DRY RUN] Marcar gap {date_str}: sin_dato_historico")
        return True
    
    asegurar_diario(conn)
    conn.execute(
        "INSERT OR REPLACE INTO tbl_schumann_diario (fecha, actividad, fuente) VALUES (?,?,?)",
        (date_str, None, "sin_dato_historico"),
    )
    conn.commit()
    logger.info(f"Gap marcado: {date_str} = sin_dato_historico")
    return True


def main():
    parser = argparse.ArgumentParser(description="Backfill missing Schumann daily records")
    parser.add_argument("--desde", required=True, help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--hasta", required=True, help="Fecha fin YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en BD")
    # NOTA tuning P3 2026-11-10: --force-resonanceone ELIMINADO. Ponía el valor de
    # HOY en fechas pasadas (corrompe historia). ResonanceOne solo sirve el dato
    # actual; backfill_from_resonanceone() ya devuelve False si fecha != hoy.
    args = parser.parse_args()
    
    # Validar rango
    try:
        datetime.strptime(args.desde, "%Y-%m-%d")
        datetime.strptime(args.hasta, "%Y-%m-%d")
    except ValueError:
        logger.error("Formato de fecha inválido. Use YYYY-MM-DD")
        return 1
    
    if args.desde > args.hasta:
        logger.error("--desde debe ser <= --hasta")
        return 1
    
    missing = find_missing_dates(args.desde, args.hasta)
    
    if not missing:
        logger.info(f"No hay fechas faltantes en rango {args.desde} a {args.hasta}")
        return 0
    
    logger.info(f"Fechas faltantes en rango {args.desde}-{args.hasta}: {len(missing)}")
    for d in missing:
        logger.info(f"  - {d}")
    
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    try:
        backfilled = 0
        gaps = 0
        
        for date_str in missing:
            # Solo intentar ResonanceOne para hoy (nunca para fechas pasadas)
            if date_str == datetime.now(timezone.utc).strftime("%Y-%m-%d"):
                if backfill_from_resonanceone(conn, date_str, args.dry_run):
                    backfilled += 1
                    continue
            
            # Marcar como gap histórico
            mark_gap(conn, date_str, args.dry_run)
            gaps += 1
        
        logger.info(f"Resumen: {backfilled} backfilled, {gaps} gaps marcados")
    finally:
        conn.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())