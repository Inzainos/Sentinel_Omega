
"""
Sentinel Omega — Network & Agent Watchdog
Levanta el sistema si ve desconexiones o fallos de red/servicio.

- Chequea conectividad cada 60s (ping 8.8.8.8 + 1.1.1.1 + http google)
- Chequea health del agente (ollama + DB) via agent_bridge si existe
- Si falla N veces seguidas => intenta `systemctl --user restart sentinel-omega` + watchdog alert
- CADA ciclo sano asegura que sentinel-omega y los dashboards de usuario
  (API FastAPI 8787 + **Dash/Plotly principal 8128**) sigan activos: unidad inactiva =>
  `systemctl --user restart` + aviso por Telegram en la primera detección
  (2026-09-28). `Restart=always` cubre el proceso muerto; esto cubre la
  unidad DETENIDA (stop manual o StartLimit agotado).
- El dashboard Streamlit (8510) es unit de USUARIO desde el 2026-10-08
  (sentinel-omega-dashboard): se vigila por PUERTO y el watchdog lo
  reinicia con `systemctl --user restart` (asegurar_streamlit). No está
  en RESTORE_UNITS a propósito: el chequeo por puerto distingue «no
  escucha» de «la unit está activa», que es justo lo que falla en un
  Streamlit colgado.
- El dashboard React/Vite legacy (5173) se mantiene pero NO está en RESTORE_UNITS.
- El Dash/Plotly principal (8128) SÍ está en RESTORE_UNITS.
- La API medic externa (:8788, proyecto /watchdog) se vigila por PUERTO:
  si no responde, el watchdog solo avisa (no la reinicia: es de otro
  proyecto).
- El /health del launcher (:8789) se lee por HTTP: 200 sano / 503 no sano
  (JSON con phase, cycle, heartbeat_age_s, consecutive_failures, reason).
  El puerto puede escuchar con el ciclo colgado, así que el chequeo por
  puerto no basta. Solo detección + aviso: el launcher se auto-reinicia
  vía systemd (sys.exit(1)/(2)); el watchdog NO lo reinicia.
- Notifica via AlertService (Telegram/Log) cuando vuelve la red
- Corre como unit de USUARIO systemd sentinel-omega-watchdog.service (Restart=always);
  todas las llamadas usan `systemctl --user` (las units de sistema estan enmascaradas)

Ojo operador: si DETIENE una unidad a propósito (mantenimiento), este watchdog
la re-levantará en <=60s. Detenga primero el watchdog
(`systemctl --user stop sentinel-omega-watchdog`) o quite la unidad de
WATCHDOG_RESTORE_UNITS en deploy/.env.

No requiere credenciales para chequear; si hay Telegram, notifica.
"""
from __future__ import annotations
import time, subprocess, logging, socket, os
import urllib.error, urllib.request
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s [WATCHDOG] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHECK_INTERVAL_S = int(os.environ.get('WATCHDOG_INTERVAL_S', '60'))
FAIL_THRESHOLD = int(os.environ.get('WATCHDOG_FAIL_THRESHOLD', '3'))
PING_HOSTS = ['8.8.8.8','1.1.1.1']
HTTP_HOSTS = ['https://www.google.com','https://api.nasa.gov']

# Sentinel corre como units de USUARIO: siempre `systemctl --user`.
SYSTEMCTL = ['systemctl', '--user']
# Units (manager de usuario) a asegurar CADA ciclo sano. Desde 2026-11-09
# incluyen: sentinel-omega (ciclo principal), API FastAPI 8787, **Dash/Plotly 8128 principal**.
# El React/Vite legacy (5173) y Streamlit legacy (8510) están fuera a propósito.
RESTORE_UNITS = [u.strip() for u in os.environ.get(
    'WATCHDOG_RESTORE_UNITS',
    'sentinel-omega,sentinel-omega-dashboard-api,sentinel-omega-dashboard-dash'
).split(',') if u.strip()]

# El Streamlit legacy (8510) se vigila por PUERTO. Desde el 2026-10-08 ya es
# unit de USUARIO --- antes vivia en /etc/systemd/system y por eso solo se
# podia mirar el puerto---, asi que `systemctl --user restart` sobre
# STREAMLIT_UNIT ya funciona. Se deja fuera de RESTORE_UNITS a proposito: el
# chequeo por puerto distingue «no escucha» de «la unit esta activa», que es
# justo lo que falla en un Streamlit colgado. Desactivable con
# WATCHDOG_STREAMLIT_CHECK=0.
STREAMLIT_CHECK = os.environ.get('WATCHDOG_STREAMLIT_CHECK', '1') == '1'
STREAMLIT_HOST = os.environ.get('WATCHDOG_STREAMLIT_HOST', '127.0.0.1')
STREAMLIT_PORT = int(os.environ.get('WATCHDOG_STREAMLIT_PORT', '8510'))
STREAMLIT_UNIT = os.environ.get('WATCHDOG_STREAMLIT_UNIT', 'sentinel-omega-dashboard')

# Estado del ciclo anterior por clave (nombre de unidad o 'streamlit') para
# avisar SOLO en la transición activa->caída, no cada ciclo.
_previo: dict = {}


def _user_systemd_env() -> dict:
    """Entorno para `systemctl --user` aun desde cron/ssh sin sesion.

    Devuelve una COPIA de os.environ (no muta el entorno global) con
    XDG_RUNTIME_DIR=/run/user/<uid> y el bus de usuario si faltan.
    """
    env = dict(os.environ)
    if not env.get('XDG_RUNTIME_DIR'):
        env['XDG_RUNTIME_DIR'] = f'/run/user/{os.getuid()}'
    if not env.get('DBUS_SESSION_BUS_ADDRESS'):
        env['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path={env['XDG_RUNTIME_DIR']}/bus"
    return env


def _systemctl(*args: str, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run([*SYSTEMCTL, *args], capture_output=True, text=True,
                          timeout=timeout, env=_user_systemd_env())


def _puerto_ok(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except Exception:
        return False


def has_network() -> bool:
    # 1) DNS + TCP check (sin depender de ping binario)
    for host in PING_HOSTS:
        try:
            socket.create_connection((host, 53), timeout=5)
            return True
        except Exception:
            continue
    # 2) fallback http
    try:
        import httpx
        for url in HTTP_HOSTS:
            try:
                with httpx.Client(timeout=5.0, follow_redirects=True) as c:
                    r = c.get(url)
                    if r.status_code < 500:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def service_active(name: str) -> bool:
    try:
        r = _systemctl('is-active', name, timeout=5)
        return r.stdout.strip() == 'active'
    except Exception:
        return False


def heartbeat_ok(heartbeat_path: str = None, max_age_s: int = 600) -> bool:
    """
    Check if launcher heartbeat is fresh.

    Args:
        heartbeat_path: Path to heartbeat file (default from data_dir)
        max_age_s: Maximum age in seconds before considering stale (default 600 = 2 cycles)

    Returns:
        True if heartbeat exists and is recent, False otherwise
    """
    try:
        import json
        from pathlib import Path

        if heartbeat_path is None:
            # Default location
            data_dir = os.environ.get('SENTINEL_DATA_DIR', '/home/deamon/Sentinel_Omega/sentinel_omega/data')
            heartbeat_path = str(Path(data_dir) / "sentinel_omega_heartbeat.json")

        hb_file = Path(heartbeat_path)
        if not hb_file.exists():
            logger.debug("Heartbeat file not found: %s", heartbeat_path)
            return False

        hb_data = json.loads(hb_file.read_text())
        hb_ts = hb_data.get("ts", 0)
        age = time.time() - hb_ts

        if age > max_age_s:
            logger.warning(f"Heartbeat stale: age={age:.0f}s > max={max_age_s}s (cycle={hb_data.get('cycle')})")
            return False

        logger.debug(f"Heartbeat OK: age={age:.0f}s, cycle={hb_data.get('cycle')}")
        return True

    except Exception as e:
        logger.debug(f"Heartbeat check failed: {e}")
        return False


def try_restart(services):
    for svc in services:
        try:
            logger.warning(f'Restart {svc}')
            r = _systemctl('restart', svc, timeout=30)
            if r.returncode != 0:
                logger.error(f'restart {svc} rc={r.returncode}: {(r.stderr or "").strip()}')
        except Exception as e:
            logger.error(f'restart {svc} fail: {e}')


def agent_ok() -> bool:
    try:
        from sentinel_omega.infrastructure.messaging.agent_bridge import agent_health
        h = agent_health()
        # ok si ollama responde o al menos DB existe
        return bool(h.get('db_exists') or h.get('ollama_ok'))
    except Exception:
        return True  # no bloquear por agente si no esta


def notify(subject: str, html: str):
    try:
        from sentinel_omega.infrastructure.messaging.alert_service import AlertService, AlertTemplates, Severity, FormattedMessage
        svc = AlertService()
        msg = FormattedMessage(html=html, markdown=html, plain=html, subject=subject, severity=Severity.AMARILLO, alert_type='WATCHDOG')
        svc.dispatch(msg, channels=['telegram','log'])
        logger.info(f'notify {subject}')
    except Exception as e:
        logger.warning(f'notify fail: {e}')
        logger.info(html)


def asegurar_unidades() -> None:
    """Cada ciclo sano: unidad de usuario inactiva => restart + aviso en la caída.

    El aviso por Telegram sale SOLO la primera vez que se detecta la caída
    (transición activa->inactiva respecto al ciclo anterior): si la unidad
    sigue caída o el restart falla, los ciclos siguientes solo lo dejan en
    el log, no spamean el chat.
    """
    for svc in RESTORE_UNITS:
        activa = service_active(svc)
        if not activa:
            logger.warning(f'{svc} inactiva => re-levantando')
            try_restart([svc])
            levantada = service_active(svc)
            logger.info(f'{svc} tras restart: {"activa" if levantada else "SIGUE INACTIVA"}')
            if _previo.get(svc) and not activa:
                notify(f'[WATCHDOG] {svc} re-levantada',
                       f'`{svc}` amaneció inactiva y el watchdog la reinició '
                       f'({"OK" if levantada else "el restart no la levantó"}). '
                       f'{datetime.now(timezone.utc).isoformat()}')
        _previo[svc] = activa


def asegurar_streamlit() -> None:
    """Streamlit (unit de USUARIO, 8510): si el puerto no responde,
    reiniciar con `systemctl --user restart` y avisar en la transición.

    2026-11-10 (P1): antes intentaba `sudo -n systemctl restart` contra
    una unit de sistema que NO existe (el restart fallaba siempre) y el
    aviso llevaba el comando manual equivocado (`sudo systemctl restart`).
    Desde el 2026-10-08 Streamlit es unit de usuario y el restart por
    --user funciona.
    """
    if not STREAMLIT_CHECK:
        return
    arriba = _puerto_ok(STREAMLIT_HOST, STREAMLIT_PORT)
    if not arriba:
        logger.warning(f'Streamlit {STREAMLIT_HOST}:{STREAMLIT_PORT} no responde => restart --user')
        r = _systemctl('restart', STREAMLIT_UNIT, timeout=30)
        if r.returncode == 0:
            logger.info(f'{STREAMLIT_UNIT} reiniciada con systemctl --user')
        else:
            logger.error(f'no se pudo reiniciar {STREAMLIT_UNIT} '
                         f'(--user rc={r.returncode}): {(r.stderr or "").strip()[:120]}')
        if _previo.get('streamlit'):
            notify('[WATCHDOG] Streamlit caído (8510)',
                   f'El dashboard Streamlit no responde en {STREAMLIT_HOST}:{STREAMLIT_PORT} '
                   f'y el watchdog intentó reiniciarlo. Levantarlo a mano:\n'
                   f'`systemctl --user restart {STREAMLIT_UNIT}`\n'
                   f'{datetime.now(timezone.utc).isoformat()}')
    _previo['streamlit'] = arriba


# La API medic externa (:8788, proyecto /watchdog, unit medic-api.service)
# se vigila por PUERTO, como Streamlit: si no responde, solo se avisa —
# NO se reinicia (es de otro proyecto; el restart lo decide su dueño).
# Desactivable con WATCHDOG_MEDIC_CHECK=0.
MEDIC_CHECK = os.environ.get('WATCHDOG_MEDIC_CHECK', '1') == '1'
MEDIC_HOST = os.environ.get('WATCHDOG_MEDIC_HOST', '127.0.0.1')
MEDIC_PORT = int(os.environ.get('WATCHDOG_MEDIC_PORT', '8788'))


def asegurar_medic() -> None:
    """Medic API externa (:8788): detectar que no responde y avisar.

    Solo detección + aviso en la transición (como Streamlit, sin restart):
    medic es un proyecto externo (/watchdog) y el watchdog no lo levanta.
    """
    if not MEDIC_CHECK:
        return
    arriba = _puerto_ok(MEDIC_HOST, MEDIC_PORT)
    if not arriba:
        logger.warning(f'Medic {MEDIC_HOST}:{MEDIC_PORT} no responde (proyecto externo /watchdog)')
        if _previo.get('medic'):
            notify('[WATCHDOG] Medic API caída (8788)',
                   f'La API medic no responde en {MEDIC_HOST}:{MEDIC_PORT}. '
                   f'Es un proyecto externo (/watchdog, unit medic-api.service): '
                   f'revisarla a mano (`systemctl --user status medic-api`).\n'
                   f'{datetime.now(timezone.utc).isoformat()}')
    _previo['medic'] = arriba


# El /health del launcher (:8789, contrato en launcher._start_health_server):
# GET http://127.0.0.1:8789/health -> 200 sano / 503 no sano, JSON con phase,
# cycle, heartbeat_age_s, consecutive_failures y reason. Se lee por HTTP, no
# por puerto: el puerto puede escuchar con el ciclo colgado (el 503 es el que
# dice que el launcher está mal). Solo detección + aviso, como medic: el
# launcher ya se auto-reinicia vía systemd (sys.exit(1)/(2) en launcher.py);
# el watchdog NO lo reinicia. Timeout corto para no bloquear el loop.
# Desactivable con WATCHDOG_HEALTH_CHECK=0.
HEALTH_CHECK = os.environ.get('WATCHDOG_HEALTH_CHECK', '1') == '1'
HEALTH_HOST = os.environ.get('WATCHDOG_HEALTH_HOST', '127.0.0.1')
HEALTH_PORT = int(os.environ.get('WATCHDOG_HEALTH_PORT', '8789'))
HEALTH_TIMEOUT_S = float(os.environ.get('WATCHDOG_HEALTH_TIMEOUT_S', '5'))


def leer_health(host: str = None, port: int = None,
                timeout: float = None) -> dict:
    """Lee GET /health del launcher y devuelve el estado como dict.

    Devuelve siempre un dict con:
      ok: True solo si HTTP 200 (el contrato del launcher: 200 sano).
      status: código HTTP, o None si no hubo respuesta.
      phase / reason / cycle / heartbeat_age_s / consecutive_failures:
        del JSON cuando lo trae (None si no hay).
      error: fallo de red/timeout/cuerpo no-JSON (None si hubo respuesta).
    Nunca lanza: cualquier fallo de red se devuelve como ok=False.
    Un 200 con cuerpo no-JSON cuenta como sano (manda el código, que es el
    contrato) pero deja el error registrado.
    """
    import json

    host = HEALTH_HOST if host is None else host
    port = HEALTH_PORT if port is None else port
    timeout = HEALTH_TIMEOUT_S if timeout is None else timeout
    url = f'http://{host}:{port}/health'
    estado = {'ok': False, 'status': None, 'phase': None, 'reason': None,
              'cycle': None, 'heartbeat_age_s': None,
              'consecutive_failures': None, 'error': None}

    def _rellenar(payload):
        if isinstance(payload, dict):
            for k in ('phase', 'reason', 'cycle', 'heartbeat_age_s',
                      'consecutive_failures'):
                estado[k] = payload.get(k)

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SentinelWatchdog/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            estado['status'] = resp.status
            try:
                _rellenar(json.loads(resp.read().decode('utf-8')))
            except Exception as exc:
                estado['error'] = f'respuesta no-JSON: {exc}'
            estado['ok'] = resp.status == 200
            return estado
    except urllib.error.HTTPError as exc:
        # HTTPError trae status + cuerpo: el 503 del launcher lleva
        # phase/reason en el JSON.
        estado['status'] = exc.code
        try:
            _rellenar(json.loads(exc.read().decode('utf-8')))
        except Exception:
            pass
        estado['reason'] = estado['reason'] or f'HTTP {exc.code}'
        estado['ok'] = False
        return estado
    except Exception as exc:
        estado['error'] = f'{type(exc).__name__}: {exc}'
        return estado


def asegurar_health() -> None:
    """Launcher /health (:8789): detectar no-sano y avisar.

    Solo detección + aviso en la transición (como medic, sin restart):
    el launcher se auto-reinicia vía systemd cuando falla (sys.exit(1)/(2)
    en launcher.py); el watchdog no lo levanta. El aviso por Telegram sale
    SOLO la primera vez que se detecta la caída (transición sano->no-sano
    respecto al ciclo anterior): si sigue no-sano, los ciclos siguientes
    solo lo dejan en el log, no spamean el chat.
    """
    if not HEALTH_CHECK:
        return
    estado = leer_health()
    sano = bool(estado['ok'])
    if not sano:
        detalle = estado.get('reason') or estado.get('error') or 'sin respuesta'
        fase = estado.get('phase')
        logger.warning(
            f'/health {HEALTH_HOST}:{HEALTH_PORT} no sano '
            f'(status={estado.get("status")} phase={fase} reason={detalle})'
        )
        if _previo.get('health'):
            notify('[WATCHDOG] Launcher /health no sano (8789)',
                   f'El launcher no está sano según /health '
                   f'({HEALTH_HOST}:{HEALTH_PORT}): status={estado.get("status")}, '
                   f'phase={fase}, reason={detalle}. '
                   f'El launcher se auto-reinicia vía systemd (sys.exit no-cero); '
                   f'si no vuelve solo, revisar a mano '
                   f'(`systemctl --user status sentinel-omega`).\n'
                   f'{datetime.now(timezone.utc).isoformat()}')
    _previo['health'] = sano


def main():
    logger.info(f'Watchdog start interval={CHECK_INTERVAL_S}s threshold={FAIL_THRESHOLD}')
    logger.info(f'Asegurar cada ciclo: {", ".join(RESTORE_UNITS)} (Dash 8128 principal)'
                + (f' + streamlit:{STREAMLIT_PORT}' if STREAMLIT_CHECK else '')
                + (f' + medic:{MEDIC_PORT}' if MEDIC_CHECK else '')
                + (f' + health:{HEALTH_PORT}' if HEALTH_CHECK else ''))
    fails = 0
    was_down = False
    heartbeat_stale_notified = False
    while True:
        net = has_network()
        ag = agent_ok()
        hb = heartbeat_ok()
        if net and ag and hb:
            if was_down:
                notify('[SENTINEL] Red restaurada', f'Red OK tras {fails} fallos. {datetime.now(timezone.utc).isoformat()}')
            # asegurar servicios arriba: cada ciclo sano, no solo tras caída
            asegurar_unidades()
            asegurar_streamlit()
            asegurar_medic()
            asegurar_health()
            fails = 0
            was_down = False
            heartbeat_stale_notified = False
            logger.info('OK net+agent+heartbeat')
        else:
            fails += 1
            logger.warning(f'FAIL net={net} agent={ag} heartbeat={hb} fails={fails}/{FAIL_THRESHOLD}')
            if fails >= FAIL_THRESHOLD:
                was_down = True
                # si no hay red, no intentar restart inmediato (esperar red), pero si hay red y agente mal, restart
                if net and not ag:
                    try_restart(['sentinel-omega'])  # scheduler disabled: duplicate launcher fought omega
                    notify('[SENTINEL] Watchdog reinicio agente', f'Agente no OK, reiniciado. fails={fails}')
                elif net and ag and not hb and not heartbeat_stale_notified:
                    # Red y agente OK pero heartbeat stale -> launcher colgado
                    logger.warning('Heartbeat stale con red/agent OK -> reiniciando sentinel-omega')
                    try_restart(['sentinel-omega'])
                    notify('[SENTINEL] Watchdog reinicio por heartbeat stale', f'Launcher no actualiza heartbeat, reiniciado. fails={fails}')
                    heartbeat_stale_notified = True
                elif not net:
                    logger.warning('Sin red, esperando restauracion...')
                    # no restart hasta que vuelva red, pero avisar una vez
                    if fails == FAIL_THRESHOLD:
                        logger.warning('Red caida, watchdog en espera')
                # si la red sigue caida, no resetear a 0 (evitar esperar 3 ciclos mas); dejar en threshold-1 para re-evaluar rapido
                fails = 0 if net else FAIL_THRESHOLD - 1
        time.sleep(CHECK_INTERVAL_S)

if __name__ == '__main__':
    main()
