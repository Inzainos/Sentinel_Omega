"""
NASA NEO (Near-Earth Objects) API connector — External gravity trigger.

Potentially hazardous asteroids passing close to Earth are treated as an
external gravitational modulator, in the same family as the lunar trigger:
not an energy source, but a possible "when" for nodes already critical.

Requires: NASA_API_KEY environment variable (falls back to DEMO_KEY,
which is rate-limited but functional).
"""

import logging
import os
import signal
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sentinel_omega.infrastructure.api.circuit_breaker import circuit
from sentinel_omega.infrastructure.api._redact import sin_credenciales

logger = logging.getLogger(__name__)

NEO_FEED_URL = "https://api.nasa.gov/neo/rest/v1/feed"
TIMEOUT = (3, 8)

_plain_session: requests.Session | None = None


def _get_plain_session() -> requests.Session:
    """Sesión SIN adaptador Retry (fix A, 2026-11-10, CYCLE TIMEOUT NEO/429).

    La sesión compartida (`_http.get_session`) monta un `Retry` que duerme
    el header `Retry-After` SIN tope (urllib3 2.8.0: `sleep_for_retry` hace
    `time.sleep(retry_after)` crudo). Con la cuota de DEMO_KEY agotada la
    API devolvió 429 con `Retry-After: 2074` y el worker durmió 2074 s;
    el `join(420)` del launcher venció y el ciclo murió (loop de 7 min,
    4 CYCLE TIMEOUT seguidos). Esta sesión no reintenta: el 429 vuelve
    de inmediato, `raise_for_status` eleva `HTTPError` y el wrapper
    fail-soft devuelve `None`. `TIMEOUT=(3, 8)` sigue acotando el socket.
    """
    global _plain_session
    if _plain_session is None:
        _plain_session = requests.Session()
        _plain_session.mount("https://", HTTPAdapter(max_retries=Retry(total=0)))
        _plain_session.mount("http://", HTTPAdapter(max_retries=Retry(total=0)))
    return _plain_session


class NeoTimeout(Exception):
    pass


def _neo_timeout_handler(signum, frame):
    raise NeoTimeout("NASA NEO API excedió timeout de 8s")


@circuit("nasa_neo")
def fetch_neo_hazard_summary(date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch today's near-Earth objects and summarize the hazardous ones.

    Returns counts plus the closest hazardous approach in lunar distances (LD),
    or None if the API is unreachable.
    """
    # T-4 (2026-11-10): fail-soft restaurado (lo tenia el clon, lo perdio
    # el vivo) — timeout 8 s / HTTP / JSON / breaker abierto devuelven None
    # en vez de abortar el ciclo alfa1 entero (data_pipeline.py:376).
    try:
        return _fetch_neo_hazard_summary_inner(date)
    except Exception as exc:
        logger.warning("NEO fetch failed (non-blocking): %s", sin_credenciales(exc))
        return None


def _fetch_neo_hazard_summary_inner(date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    api_key = os.environ.get("NASA_API_KEY", "DEMO_KEY")
    day = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    params = {"start_date": day, "end_date": day, "api_key": api_key}

    # T2-2 (2026-11-10): guard de hilo principal — signal.signal /
    # signal.alarm solo funcionan en el hilo principal. El launcher corre
    # el ciclo en un worker thread ("cycle-worker"): sin este guard,
    # signal.signal elevaba ValueError 1x por ciclo y el fail-soft del
    # wrapper devolvía None (se perdía el dato NEO de ese ciclo). En otro
    # hilo no se arma alarma y el timeout lo pone requests: TIMEOUT (3, 8).
    is_main_thread = threading.current_thread() is threading.main_thread()
    if is_main_thread:
        signal.signal(signal.SIGALRM, _neo_timeout_handler)
        signal.alarm(8)
    try:
        resp = _get_plain_session().get(NEO_FEED_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if is_main_thread:
            signal.alarm(0)

    objects = data.get("near_earth_objects", {}).get(day, [])
    hazardous = [o for o in objects if o.get("is_potentially_hazardous_asteroid")]

    closest_ld = None
    closest_name = ""
    for o in hazardous:
        for approach in o.get("close_approach_data", []):
            try:
                ld = float(approach["miss_distance"]["lunar"])
            except (KeyError, TypeError, ValueError):
                continue
            if closest_ld is None or ld < closest_ld:
                closest_ld = ld
                closest_name = o.get("name", "")

    result = {
        "total_count": len(objects),
        "hazardous_count": len(hazardous),
        "closest_hazardous_ld": closest_ld,
        "closest_hazardous_name": closest_name,
        "date": day,
    }
    logger.info(
        f"NEO feed: {result['total_count']} objects, "
        f"{result['hazardous_count']} hazardous"
        + (f", closest {closest_ld:.1f} LD" if closest_ld is not None else "")
    )
    return result
