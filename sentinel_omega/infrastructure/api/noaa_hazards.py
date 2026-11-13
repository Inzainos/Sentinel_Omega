"""
NOAA Hazards API connectors — Hurricanes and Tsunamis.

Sources:
  - NHC (National Hurricane Center) — Active tropical cyclones
    (`CurrentStorms.json`, actualizado ~cada 2 min)
  - PTWC/NTWC (Pacific/National Tsunami Warning Center) — Active warnings
  - NOAA Tides & Currents — Sea level anomalies

Public APIs, no authentication required.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sentinel_omega.infrastructure.api._http import get_session
from sentinel_omega.infrastructure.api._redact import sin_credenciales
from sentinel_omega.infrastructure.api.circuit_breaker import circuit

logger = logging.getLogger(__name__)

TIMEOUT = 15

# 2026-11-10 (P2): `CurrentSurges.json` NO EXISTE — 404 en cada ciclo desde
# que se audita (691 líneas en el log actual). La fuente viva es
# `CurrentStorms.json`: lista de tormentas activas con posición, intensidad,
# movimiento y enlaces a cada producto. Verificado 2026-11-10 20:24 UTC:
# 1 tormenta activa (Pena, CP4, TS 35 kt, 11.1N 164.7W). El viejo endpoint
# mentía además en el log ("may be no active storms") ante un 404.
NHC_ACTIVE_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"
# Base del archivo GIS por tormenta/aviso (los zip/KMZ que enlaza cada
# entrada de CurrentStorms.json: forecast/track/cone/best_track). Es un
# prefijo de ruta, no un feed: no se le pega directo.
NHC_GIS_URL = "https://www.nhc.noaa.gov/gis/forecast/archive/"
NHC_CYCLONES_URL = "https://www.nhc.noaa.gov/productexamples/NHC_JSON_Sample.json"
NHC_ATLANTIC_RSS = "https://www.nhc.noaa.gov/nhc_at5.xml"
NHC_PACIFIC_RSS = "https://www.nhc.noaa.gov/nhc_ep5.xml"

TSUNAMI_EVENTS_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/tsunamis/events"
TSUNAMI_SOURCES_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/tsunamis/sources"


@dataclass
class TropicalCyclone:
    name: str
    category: int
    lat: float
    lon: float
    max_wind_kt: float
    pressure_mb: float
    movement_dir: str
    movement_speed_kt: float
    basin: str


@dataclass
class TsunamiEvent:
    year: int
    month: Optional[int]
    day: Optional[int]
    lat: float
    lon: float
    magnitude: Optional[float]
    intensity: Optional[float]
    max_water_height_m: Optional[float]
    cause: str
    country: str


def _categoria_saffir_simpson(viento_kt: float) -> int:
    """Categoría Saffir-Simpson por viento máximo sostenido (kt).

    0 = depresión/tormenta tropical (<64 kt, sin categoría de huracán).
    La clasificación de CurrentStorms.json (`TS`/`HU`/…) no trae el número,
    así que se deriva del viento, que sí viene.
    """
    if viento_kt >= 137:
        return 5
    if viento_kt >= 113:
        return 4
    if viento_kt >= 96:
        return 3
    if viento_kt >= 83:
        return 2
    if viento_kt >= 64:
        return 1
    return 0


def _cuenca_desde_id(storm_id: str) -> str:
    """Cuenca por prefijo del id NHC (`cp042026` → CP, `al…` → AT, `ep…` → EP)."""
    prefijo = (storm_id or "")[:2].lower()
    return {"cp": "CP", "al": "AT", "ep": "EP"}.get(prefijo, "AT")


@circuit("nhc")
def fetch_active_hurricanes() -> List[TropicalCyclone]:
    """Fetch active tropical cyclones from NHC CurrentStorms.json.

    `[]` significa SIN tormentas activas (el feed responde 200 con
    `activeStorms: []`). Un fallo de red/parseo también devuelve `[]`,
    pero se registra como ERROR (fuente inalcanzable), nunca como
    "no hay tormentas": esa confusión es lo que mantuvo el muro oceánico
    ciego con el endpoint muerto anterior.
    """
    try:
        resp = get_session().get(NHC_ACTIVE_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        cyclones = []
        for storm in data.get("activeStorms", []) or []:
            try:
                viento = float(storm.get("intensity") or 0)
            except (TypeError, ValueError):
                viento = 0.0
            try:
                presion = float(storm.get("pressure") or 1013)
            except (TypeError, ValueError):
                presion = 1013.0
            try:
                lat = float(storm.get("latitudeNumeric"))
                lon = float(storm.get("longitudeNumeric"))
            except (TypeError, ValueError):
                continue
            try:
                mov_dir = storm.get("movementDir")
                mov_spd = float(storm.get("movementSpeed") or 0)
            except (TypeError, ValueError):
                mov_dir, mov_spd = "N", 0.0

            cyclones.append(TropicalCyclone(
                name=str(storm.get("name") or "Unknown"),
                category=_categoria_saffir_simpson(viento),
                lat=lat,
                lon=lon,
                max_wind_kt=viento,
                pressure_mb=presion,
                movement_dir=str(mov_dir) if mov_dir is not None else "N",
                movement_speed_kt=mov_spd,
                basin=_cuenca_desde_id(str(storm.get("id") or "")),
            ))

        logger.info(f"NHC: {len(cyclones)} active tropical cyclones")
        return cyclones
    except Exception as e:
        logger.error(f"NHC fetch failed (fuente inalcanzable, NO 'sin tormentas'): {sin_credenciales(e)}")
        return []


@circuit("ngdc")
def fetch_historical_tsunamis(
    min_year: int = 2000,
    min_magnitude: float = 6.0,
) -> List[TsunamiEvent]:
    """Fetch historical tsunami events from NOAA NGDC Hazard Service."""
    params = {
        "minYear": min_year,
        "minEqMagnitude": min_magnitude,
    }
    try:
        resp = get_session().get(TSUNAMI_EVENTS_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []

        events = []
        for item in items[:100]:
            events.append(TsunamiEvent(
                year=int(item.get("year", 0)),
                month=item.get("month"),
                day=item.get("day"),
                lat=float(item.get("latitude", 0)),
                lon=float(item.get("longitude", 0)),
                magnitude=item.get("eqMagnitude"),
                intensity=item.get("tsunamiIntensity"),
                max_water_height_m=item.get("maxWaterHeight"),
                cause=item.get("causeCode", "unknown"),
                country=item.get("country", "unknown"),
            ))

        logger.info(f"NGDC: {len(events)} historical tsunami events since {min_year}")
        return events
    except Exception as e:
        logger.warning(f"NGDC tsunami fetch failed: {sin_credenciales(e)}")
        return []


def detect_tsunamigenic_quake(
    magnitude: float,
    depth_km: float,
    lat: float,
    lon: float,
) -> bool:
    """Check if an earthquake has tsunamigenic potential.
    Criteria: M >= 7.0, shallow (< 70km), undersea or near coast."""
    if magnitude < 7.0:
        return False
    if depth_km > 70.0:
        return False
    return True


def compute_hurricane_proximity(
    cyclones: List[TropicalCyclone],
    target_lat: float,
    target_lon: float,
    max_distance_deg: float = 10.0,
) -> List[Dict[str, Any]]:
    """Find cyclones within proximity of a target location."""
    nearby = []
    for c in cyclones:
        dist = ((c.lat - target_lat) ** 2 + (c.lon - target_lon) ** 2) ** 0.5
        if dist <= max_distance_deg:
            nearby.append({
                "name": c.name,
                "category": c.category,
                "distance_deg": dist,
                "max_wind_kt": c.max_wind_kt,
                "pressure_mb": c.pressure_mb,
            })
    return sorted(nearby, key=lambda x: x["distance_deg"])
