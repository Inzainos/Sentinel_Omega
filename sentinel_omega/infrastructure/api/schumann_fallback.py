"""
Fallback Schumann data sources for Sentinel Omega.

Prioridad:
1. Tomsk sos70.ru — fuente primaria, corte diario.
2. ResonanceOne API — fallback para actividad diaria cuando Tomsk está caído (backup station Etna, Sicilia).
3. schumannresonance.today — referencia humana, no usada en pipeline.

Este módulo expone fetch_schumann_fallback() que devuelve (hz, actividad_pct, fuente)
o None si no hay alternativa disponible.
"""

from __future__ import annotations
import logging
from typing import Optional, Tuple
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

from sentinel_omega.infrastructure.api.circuit_breaker import circuit

RESONANCEONE_API = "https://resonanceone.app/api/now"

@circuit("resonanceone")
def fetch_resonanceone() -> Optional[Tuple[float, float, str, dict]]:
    """
    Obtiene datos de Schumann desde ResonanceOne API.
    
    ResonanceOne proporciona:
    - schumann_index: 0-100 (componente Schumann del Activity Index)
    - schumann_frequency_hz: frecuencia nominal 7.83 Hz
    - schumann_unavailable: bool
    - backup_station: bool (Etna, Sicilia cuando Tomsk offline)
    - data_quality: "backup" o "live"
    - confidence_score: 0-100
    - data_source: "etna" o "tomsk"
    
    Mapea schumann_index (0-100) a actividad_pct comparable con Tomsk WPC.
    Retorna: (freq_hz, actividad_pct_calibrada, fuente, metadata_dict)
    """
    if httpx is None:
        logger.warning("httpx no disponible, no se puede usar ResonanceOne fallback")
        return None
    
    try:
        resp = httpx.get(RESONANCEONE_API, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("ResonanceOne API falló: %s", e)
        return None
    
    # Verificar si hay datos de Schumann
    if data.get("schumann_unavailable", True):
        logger.info("ResonanceOne: Schumann no disponible")
        return None
    
    schumann_index = data.get("schumann_index")
    if schumann_index is None:
        logger.info("ResonanceOne: sin schumann_index")
        return None
    
    # Calibración: schumann_index 0-100 -> actividad_pct estilo Tomsk WPC
    # Tomsk WPC típico: 1-3% (píxeles blancos en ROI)
    # ResonanceOne schumann_index típico backup (Etna): ~39
    # Factor empírico conservador: 0.07 para mapear a rango Tomsk
    # 39 * 0.07 = 2.73% (en rango Tomsk típico 1-3%)
    # Esto es conservador y ajustable cuando haya datos de solape
    CALIBRATION_FACTOR = 0.07
    actividad_pct = float(schumann_index) * CALIBRATION_FACTOR
    actividad_pct = max(0.0, min(actividad_pct, 10.0))  # clamp razonable
    
    freq = data.get("schumann_frequency_hz", 7.83)
    backup = data.get("backup_station", False)
    calidad = data.get("data_quality", "unknown")
    confidence = data.get("confidence_score", 0)
    data_source = data.get("data_source", "unknown")
    
    if backup:
        fuente = "resonanceone_backup"
    else:
        fuente = "resonanceone_live"
    
    metadata = {
        "schumann_index_raw": float(schumann_index),
        "activity_index": data.get("activity_index"),
        "kp_index": data.get("kp_index"),
        "solar_flare_class": data.get("solar_flare_class"),
        "geomagnetic_status": data.get("geomagnetic_status"),
        "backup_station": backup,
        "calidad": calidad,
        "confidence_score": confidence,
        "data_source": data_source,
        "last_schumann_at": data.get("last_schumann_at"),
        "observation_window": data.get("observation_window"),
        "calibration_factor": CALIBRATION_FACTOR,
    }
    
    logger.info("ResonanceOne fallback: schumann_index=%.1f -> actividad=%.2f%%, freq=%.2f Hz, fuente=%s, calidad=%s, confidence=%s", 
                float(schumann_index), actividad_pct, freq, fuente, calidad, confidence)
    return (freq, actividad_pct, fuente, metadata)


def fetch_schumannresonance_today_reference() -> Optional[dict]:
    """
    Referencia humana desde schumannresonance.today/archive.
    No se usa para pipeline, solo para auditoría/comparación.
    """
    logger.debug("schumannresonance.today usado como referencia manual, no como fuente de datos")
    return None


def fetch_schumann_fallback() -> Optional[Tuple[float, float, str, dict]]:
    """
    Intenta fuentes de fallback en orden.
    Retorna (hz, actividad_pct, fuente, metadata) o None.
    """
    # 1. ResonanceOne (backup station Etna cuando Tomsk offline)
    res = fetch_resonanceone()
    if res:
        return res

    # 2. Referencia manual
    logger.info("Fallback Schumann agotado — operando en modo degradado con LOCF")
    return None
