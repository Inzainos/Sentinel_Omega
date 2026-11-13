"""
Geophysical data connector — IERS LOD and Lunar ephemeris.
All public data, no authentication required.

Sources:
  - IERS Bulletin A (Length of Day excess, UT1-UTC)
  - PyEphem (Lunar phase computation)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

import numpy as np
import pandas as pd
from sentinel_omega.infrastructure.api._http import get_session
from sentinel_omega.infrastructure.api._redact import sin_credenciales
from sentinel_omega.infrastructure.api.circuit_breaker import circuit

logger = logging.getLogger(__name__)

IERS_FINALS_URL = "https://maia.usno.navy.mil/ser7/finals.daily"
# datacenter.iers.org (BKG) caído para clientes externos desde el 2026-10-24:
# el WAF responde 400 a TODO (incluso a la raíz, con User-Agent de navegador).
# El Bulletin A vive en USNO/Maia con el mismo dato y formato ancho fijo.
#
# finals.daily trae ~180 días; finals.all cubre 1973→hoy+1 año de predicción
# (LOD vacío en la cola de predicción lejana --- "NOT ALWAYS FILLED" en el
# readme --- y el parser lo salta). Es el que hace falta para rellenar el LOD
# histórico de tbl_astronomia_cinematica, que estaba en 0.0 en sus 280.352
# filas.
#
# Formato ancho fijo (ser7/readme.finals): MJD en cols 8-15, LOD en cols
# 80-86 en ms. Verificado contra el archivo real el 2026-10-25.
IERS_FINALS_ALL_URL = "https://maia.usno.navy.mil/ser7/finals.all"
TIMEOUT = 20


@circuit("iers")
def fetch_lod_series(days: int = 90, historico: bool = False) -> Optional[pd.DataFrame]:
    """
    Fetch Length-of-Day excess (LOD) from IERS Bulletin A finals data.
    LOD is the deviation of day length from 86400 SI seconds (in ms).
    """
    try:
        url = IERS_FINALS_ALL_URL if historico else IERS_FINALS_URL
        resp = get_session().get(url, timeout=TIMEOUT * (3 if historico else 1))
        resp.raise_for_status()

        # Ancho fijo (ser7/readme.finals): MJD cols 8-15, LOD cols 80-86 (ms).
        # Las líneas de predicción lejana traen LOD vacío: se saltan, no se
        # inventan (regla 2).
        records = []
        for line in resp.text.strip().split("\n"):
            mjd_str = line[7:15].strip()
            lod_str = line[79:86].strip()
            if not mjd_str or not lod_str:
                continue
            try:
                records.append({"mjd": float(mjd_str), "lod_ms": float(lod_str)})
            except ValueError:
                continue

        if not records:
            logger.warning("No valid LOD records parsed from IERS")
            return None

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["mjd"] + 2400000.5, unit="D", origin="julian")
        df = df.sort_values("date").tail(days).reset_index(drop=True)
        logger.info(f"Fetched {len(df)} LOD records from IERS")
        return df[["date", "lod_ms"]]

    except Exception as e:
        logger.error(f"IERS LOD fetch failed: {sin_credenciales(e)}")
        return None


def compute_lunar_phase(date: Optional[datetime] = None) -> Dict[str, float]:
    """
    Compute current lunar phase using PyEphem.
    Returns phase fraction (0=new, 0.5=full, 1=new again) and illumination %.
    """
    try:
        import ephem
    except ImportError:
        logger.warning("ephem not installed — returning default lunar phase")
        return {"phase_fraction": 0.5, "illumination_pct": 50.0, "phase_angle_deg": 180.0}

    if date is None:
        date = datetime.now(timezone.utc)

    moon = ephem.Moon(date)
    phase_pct = moon.phase
    illumination = phase_pct

    next_new = ephem.next_new_moon(date)
    prev_new = ephem.previous_new_moon(date)
    cycle_length = float(next_new - prev_new)
    days_since_new = float(ephem.Date(date) - prev_new)
    phase_fraction = days_since_new / cycle_length if cycle_length > 0 else 0.5

    phase_angle = phase_fraction * 360.0

    logger.info(
        f"Lunar phase: {phase_fraction:.3f} (illum={illumination:.1f}%, "
        f"angle={phase_angle:.1f}°)"
    )
    return {
        "phase_fraction": round(phase_fraction, 4),
        "illumination_pct": round(illumination, 2),
        "phase_angle_deg": round(phase_angle, 2),
    }


def compute_lunar_phase_series(days: int = 30) -> np.ndarray:
    """
    Compute lunar phase fraction for the past N days.
    Returns array of phase fractions (0-1).
    """
    try:
        import ephem
    except ImportError:
        return np.full(days, 0.5)

    from datetime import timedelta

    now = datetime.now(timezone.utc)
    phases = []
    for d in range(days, 0, -1):
        target = now - timedelta(days=d)
        next_new = ephem.next_new_moon(target)
        prev_new = ephem.previous_new_moon(target)
        cycle = float(next_new - prev_new)
        elapsed = float(ephem.Date(target) - prev_new)
        phases.append(elapsed / cycle if cycle > 0 else 0.5)

    return np.array(phases)
