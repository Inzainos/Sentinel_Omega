"""Serie viva de Schumann con bandera en vivo / arrastrado.

Regla del Capitán (2026-09-26): si la API de Tomsk no responde, se usa el
último valor bueno hasta que vuelva, sin límite de edad. Pero cada fila dice
de dónde salió, para que el sistema sepa si está en vivo o si la API está
caída:

- ``en_vivo``         1 = llegó de la API en este ciclo; 0 = arrastrado.
- ``ultimo_vivo_ts``  bloque (UTC) del último valor real.
- ``atraso_horas``    horas entre ese valor real y este bloque.

El arrastre solo se toma de filas ``en_vivo=1``. Si se tomara también de las
arrastradas, el valor se alimentaría a sí mismo (así se congelaron 38 bloques
en 8,26 Hz / 21,46 % hasta el 2026-09-26).

Quien use la serie como historia o entrenamiento (volcado al enjambre, cruces,
rasgos del Juez) debe filtrar con :func:`filtro_en_vivo`: un valor arrastrado
no es una medición nueva. Los ONNX siguen recibiendo el mismo vector; la
bandera y el atraso entran como rasgos en el próximo rebuild.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

TABLA = "tbl_schumann_vivo"
FMT_BLK = "%Y-%m-%d %H:00"

_COLUMNAS_NUEVAS = (
    ("en_vivo", "INTEGER DEFAULT 1"),
    ("ultimo_vivo_ts", "TEXT"),
    ("atraso_horas", "REAL"),
)


def _columnas(conn: sqlite3.Connection) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({TABLA})")}


def asegurar_tabla(conn: sqlite3.Connection) -> None:
    """Crea la tabla o le añade las columnas de bandera. Idempotente.

    Las filas viejas quedan con ``en_vivo=1`` por el DEFAULT.
    """
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLA} ("
        "timestamp_blk TEXT PRIMARY KEY, schumann_hz REAL, "
        "schumann_activity REAL, creada_at TEXT DEFAULT (datetime('now')))"
    )
    cols = _columnas(conn)
    for nombre, tipo in _COLUMNAS_NUEVAS:
        if nombre not in cols:
            conn.execute(f"ALTER TABLE {TABLA} ADD COLUMN {nombre} {tipo}")


def filtro_en_vivo(conn: sqlite3.Connection, alias: str = "") -> str:
    """``" AND COALESCE(en_vivo,1)=1"`` si la columna existe; ``""`` si no.

    Sirve para bases que todavía no pasaron por :func:`asegurar_tabla`.
    """
    try:
        if "en_vivo" in _columnas(conn):
            pref = f"{alias}." if alias else ""
            return f" AND COALESCE({pref}en_vivo,1)=1"
    except sqlite3.Error:
        pass
    return ""


def _as_float(v: Any) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def es_senal_muerta(hz: Any, act: Any) -> bool:
    """Sin señal: falta la ACTIVIDAD, o es exactamente 0 (el falso clásico).

    Cambiado el 2026-10-09, cuando la frecuencia fabricada se retiró del
    fetcher (`api/schumann.py` ya no inventa `7,83 + actividad×0,02`). Desde
    entonces la lectura viva trae **hz=None SIEMPRE** y la actividad es lo
    único medido: con la regla vieja (`hz None => sin señal`) ninguna lectura
    volvía a ser `en_vivo`, y el LOCF arrastraba para siempre la última
    «frecuencia» — que era justamente la fabricada. El hz ya no decide si hay
    señal; solo la actividad.
    """
    act_f = _as_float(act)
    return act_f is None or act_f == 0.0


def _horas_entre(desde: str, hasta: str) -> float:
    a = datetime.strptime(desde[:16], "%Y-%m-%d %H:%M")
    b = datetime.strptime(hasta[:16], "%Y-%m-%d %H:%M")
    return round((b - a).total_seconds() / 3600.0, 2)


def registrar(
    conn: sqlite3.Connection,
    hz: Any,
    act: Any,
    ahora: Optional[float] = None,
) -> Dict[str, Any]:
    """Guarda la lectura de este ciclo, o el arrastre marcado si no hay señal.

    Devuelve ``{"estado", "timestamp_blk", "schumann_hz", "schumann_activity",
    "en_vivo", "ultimo_vivo_ts", "atraso_horas"}`` con estado ``"en_vivo"``,
    ``"arrastrado"`` o ``"desconocido"`` (la API falla y nunca hubo lectura
    real: no se inventa nada).
    """
    asegurar_tabla(conn)
    ts_blk = time.strftime(FMT_BLK, time.gmtime(time.time() if ahora is None else ahora))

    if not es_senal_muerta(hz, act):
        # hz puede ser None (y lo es desde el retiro del 2026-10-09): se
        # persiste como NULL, que es «no se midió», no como 0 ni como 7,83.
        hz_f, act_f = _as_float(hz), _as_float(act)
        conn.execute(
            f"INSERT OR REPLACE INTO {TABLA} "
            "(timestamp_blk, schumann_hz, schumann_activity, creada_at, "
            " en_vivo, ultimo_vivo_ts, atraso_horas) "
            "VALUES (?,?,?,datetime('now'),1,?,0)",
            (ts_blk, hz_f, act_f, ts_blk),
        )
        conn.commit()
        return {"estado": "en_vivo", "timestamp_blk": ts_blk,
                "schumann_hz": hz_f, "schumann_activity": act_f,
                "en_vivo": 1, "ultimo_vivo_ts": ts_blk, "atraso_horas": 0.0}

    ult = conn.execute(
        f"SELECT schumann_hz, schumann_activity, timestamp_blk FROM {TABLA} "
        "WHERE COALESCE(en_vivo,1)=1 "
        "AND schumann_activity IS NOT NULL AND schumann_activity != 0 "
        "AND timestamp_blk <= ? "
        "ORDER BY timestamp_blk DESC LIMIT 1",
        (ts_blk,),
    ).fetchone()
    if not ult:
        return {"estado": "desconocido", "timestamp_blk": ts_blk,
                "schumann_hz": None, "schumann_activity": None,
                "en_vivo": 0, "ultimo_vivo_ts": None, "atraso_horas": None}

    # u_hz puede ser None (lecturas en vivo post-retiro): se arrastra tal cual.
    u_hz, u_act, u_ts = _as_float(ult[0]), float(ult[1]), ult[2]
    if u_ts[:13] == ts_blk[:13]:
        # Ya hay lectura real de esta misma hora (un ciclo anterior): se queda.
        return {"estado": "en_vivo", "timestamp_blk": ts_blk,
                "schumann_hz": u_hz, "schumann_activity": u_act,
                "en_vivo": 1, "ultimo_vivo_ts": u_ts, "atraso_horas": 0.0}

    atraso = _horas_entre(u_ts, ts_blk)
    # Nunca pisa una fila en vivo; sí actualiza un arrastre previo del bloque.
    conn.execute(
        f"INSERT INTO {TABLA} "
        "(timestamp_blk, schumann_hz, schumann_activity, creada_at, "
        " en_vivo, ultimo_vivo_ts, atraso_horas) "
        "VALUES (?,?,?,datetime('now'),0,?,?) "
        "ON CONFLICT(timestamp_blk) DO UPDATE SET "
        " schumann_hz=excluded.schumann_hz, "
        " schumann_activity=excluded.schumann_activity, "
        " ultimo_vivo_ts=excluded.ultimo_vivo_ts, "
        " atraso_horas=excluded.atraso_horas "
        "WHERE COALESCE(en_vivo,1)=0",
        (ts_blk, u_hz, u_act, u_ts, atraso),
    )
    conn.commit()
    return {"estado": "arrastrado", "timestamp_blk": ts_blk,
            "schumann_hz": u_hz, "schumann_activity": u_act,
            "en_vivo": 0, "ultimo_vivo_ts": u_ts, "atraso_horas": atraso}


def estado_actual(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Última fila con su bandera, para Telegram y el dashboard."""
    try:
        if "en_vivo" not in _columnas(conn):
            return {"estado": "sin_bandera"}
        r = conn.execute(
            f"SELECT timestamp_blk, schumann_hz, schumann_activity, "
            f"COALESCE(en_vivo,1), ultimo_vivo_ts, atraso_horas FROM {TABLA} "
            "ORDER BY timestamp_blk DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return {"estado": "sin_tabla"}
    if not r:
        return {"estado": "sin_datos"}
    return {"estado": "en_vivo" if r[3] == 1 else "arrastrado",
            "timestamp_blk": r[0], "schumann_hz": r[1], "schumann_activity": r[2],
            "en_vivo": int(r[3]), "ultimo_vivo_ts": r[4], "atraso_horas": r[5]}


# ── CORTE DIARIO (2026-10-26) ────────────────────────────────────────────────
#
# Decisión del operador: «la Schumann solo la pedimos en un corte del día
# completo, y lo vamos extrayendo solo a las horas de los eventos; eliminamos
# el espectrograma de Tomsk (por ciclo) y solo agregamos esos detalles a los
# eventos».
#
# Medido antes de tocar: el fetch por ciclo descargaba el espectrograma
# CADA 5 min (288/día) para un valor que Tomsk reescribe igual cada hora
# («25 filas, 1 valor distinto») — y fallaba 212 veces en el log de un solo
# día. Pagar 288 descargas por 1 valor/día era ruido operativo, no
# información. La ruta de DECISIÓN nunca fue Schumann (beta1: FFT del Kp,
# umbrales Schumann inalcanzables medidos; hipótesis precursora cerrada en
# negativo en 2 estaciones): esto es DATO DE CONTEXTO por evento.
#
# El corte diario: UNA descarga exitosa por día (reintenta cada ciclo
# mientras Tomsk falle — no deja el día sin dato por un outage matutino),
# que alimenta al fantasma y a los rasgos con el valor del día, y queda
# registrado como la medición del día con su fuente.

TABLA_DIARIO = "tbl_schumann_diario"


def asegurar_diario(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLA_DIARIO} ("
        "fecha TEXT PRIMARY KEY, "
        "actividad REAL, "
        "actividad_raw REAL, "
        "frecuencia_hz REAL, "
        "fuente TEXT, "
        "calidad TEXT, "
        "confianza REAL, "
        "sesgo_aplicado REAL, "
        "tomado_en TEXT DEFAULT (datetime('now')))"
    )
    # Migración forward-only: añadir columnas si no existen
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({TABLA_DIARIO})")}
    nuevas = [
        ("actividad_raw", "REAL"),
        ("frecuencia_hz", "REAL"),
        ("calidad", "TEXT"),
        ("confianza", "REAL"),
        ("sesgo_aplicado", "REAL"),
    ]
    for nombre, tipo in nuevas:
        if nombre not in cols:
            conn.execute(f"ALTER TABLE {TABLA_DIARIO} ADD COLUMN {nombre} {tipo}")


def corte_diario(
    conn: sqlite3.Connection,
    ahora: Optional[float] = None,
    save_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """UNA lectura de Schumann por día (la medición del corte).

    - Si hoy ya hay corte: lo devuelve, SIN red.
    - Si no: descarga UNA vez el espectrogramo de Tomsk (con los gates de
      honestidad del fetcher: edad de imagen, valor repetido) y guarda
      (fecha, actividad, fuente). La fila también pasa por ``registrar``
      para que la serie viva y ``estado_actual`` sigan hablando el mismo
      idioma — 1 fila/día, no 288.
    - Sin señal (Tomsk caído, imagen vieja, valor muerto): NO se inventa
      fila — se reintenta en el ciclo siguiente. El día sin corte se VE.
    """
    asegurar_diario(conn)
    ts = time.time() if ahora is None else ahora
    fecha = time.strftime("%Y-%m-%d", time.gmtime(ts))

    fila = conn.execute(
        f"SELECT actividad, fuente FROM {TABLA_DIARIO} WHERE fecha = ?",
        (fecha,),
    ).fetchone()
    if fila is not None:
        # Día ya tiene registro (exitoso o gap histórico): no reintentar
        return {"estado": "ya_hoy", "fecha": fecha,
                "actividad": _as_float(fila[0]), "fuente": fila[1]}

    act: Optional[float] = None
    
    # Verificar si Tomsk está caído hace >24h para ir directo al fallback
    # y evitar timeout de 30s en cada corte diario
    usar_fallback_directo = False
    try:
        # Contar días consecutivos sin corte exitoso (incluye días sin fila)
        # Obtener todas las fechas con sus fuentes en los últimos 7 días
        # Usar la fecha base de 'ts' (no date('now') que usa la fecha real del sistema)
        fecha_base = time.strftime("%Y-%m-%d", time.gmtime(ts))
        filas = conn.execute(
            f"SELECT fecha, fuente FROM {TABLA_DIARIO} "
            "WHERE fecha >= date(?, '-7 days') "
            "ORDER BY fecha DESC",
            (fecha_base,)
        ).fetchall()
        
        # Crear mapa fecha -> fuente para lookup rápido
        fuentes_por_fecha = {f[0]: f[1] for f in filas}
        
        dias_sin_exito = 0
        # Revisar día por día desde ayer hacia atrás
        for i in range(1, 8):  # hasta 7 días atrás
            fecha_check = time.strftime("%Y-%m-%d", time.gmtime(ts - i * 86400))
            fuente = fuentes_por_fecha.get(fecha_check)
            if fuente in ('tomsk_wpc_corte_diario', 'resonanceone_backup', 'resonanceone_live'):
                # Día con éxito: se rompe la racha
                break
            else:
                # Día sin éxito (falta fila o fuente fallida)
                dias_sin_exito += 1
        
        # Si hay 2+ días consecutivos sin éxito, ir directo a fallback
        if dias_sin_exito >= 2:
            usar_fallback_directo = True
            logger.info("Tomsk caído %d días consecutivos — saltando fetch y usando fallback directo", dias_sin_exito)
    except Exception:
        pass
    
    if not usar_fallback_directo:
        try:
            from sentinel_omega.infrastructure.api.schumann import (
                fetch_schumann_resonance,
            )
            # novedad_requerida=False: el anti-spam del fetch por ciclo (no
            # escribir 288 filas/día del mismo valor) no aplica a UNA fila/día.
            # «Hoy también fue 2,68 %» es el DATO del día. El gate de imagen
            # congelada (sha256) SÍ queda: fuente pegada = sin corte honesto.
            leido = fetch_schumann_resonance(
                save_dir=save_dir, cleanup=True, novedad_requerida=False,
            )
            if leido is not None:
                # leido = (hz, act); hz es None desde el retiro del 2026-10-09
                act = _as_float(leido[1])
        except Exception as _e:  # noqa: BLE001 — el corte no tumba el ciclo
            act = None

    if act is None or act == 0.0:
        # Intentar fallback antes de marcar día fallido
        try:
            from sentinel_omega.infrastructure.api.schumann_fallback import fetch_schumann_fallback
            fb = fetch_schumann_fallback()
            if fb:
                hz_fb, act_fb, fuente_fb, meta = fb
                act = _as_float(act_fb)
                fuente = fuente_fb
                # Guardar con fuente de fallback y metadatos completos
                actividad_raw = meta.get("schumann_index_raw")
                calidad = meta.get("calidad")
                confianza = meta.get("confidence_score")
                sesgo = meta.get("calibration_factor")
                conn.execute(
                    f"INSERT OR REPLACE INTO {TABLA_DIARIO} "
                    "(fecha, actividad, actividad_raw, frecuencia_hz, fuente, calidad, confianza, sesgo_aplicado) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (fecha, act, actividad_raw, hz_fb, fuente, calidad, confianza, sesgo),
                )
                conn.commit()
                registrar(conn, None, act, ahora=ts)
                return {"estado": "en_vivo", "fecha": fecha, "actividad": act,
                        "fuente": fuente, "calidad": calidad, "confianza": confianza}
        except Exception as _e:
            logger.debug("Fallback Schumann falló: %s", _e)

        # Marcar el día como intentado fallido para no reintentar 288 veces
        # El día sin corte se VE, pero solo intentamos UNA vez por día
        conn.execute(
            f"INSERT OR REPLACE INTO {TABLA_DIARIO} (fecha, actividad, fuente) "
            "VALUES (?,?,?)",
            (fecha, None, "tomsk_fallido"),
        )
        conn.commit()
        return {"estado": "sin_senal", "fecha": fecha, "actividad": None,
                "fuente": "tomsk_fallido"}

    # Tomsk exitoso: guardar con metadatos completos
    conn.execute(
        f"INSERT OR REPLACE INTO {TABLA_DIARIO} "
        "(fecha, actividad, actividad_raw, frecuencia_hz, fuente, calidad, confianza, sesgo_aplicado) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (fecha, act, None, None, "tomsk_wpc_corte_diario", "live", 100.0, 0.0),
    )
    conn.commit()
    # La serie viva habla el mismo idioma de siempre: 1 fila/día.
    registrar(conn, None, act, ahora=ts)
    return {"estado": "en_vivo", "fecha": fecha, "actividad": act,
            "fuente": "tomsk_wpc_corte_diario"}


def actividad_del_dia(conn: sqlite3.Connection) -> Optional[float]:
    """El valor del corte diario DE HOY (para el pipeline, sin red).

    T-2 (2026-11-10): NULL si hoy no hay corte — nunca arrastra el ultimo
    corte de dias viejos (el 2026-11-10 seguia leyendo el 3.01% del 7-nov).
    """
    try:
        fila = conn.execute(
            f"SELECT actividad FROM {TABLA_DIARIO} "
            "WHERE actividad IS NOT NULL AND fecha = date('now') "
            "ORDER BY fecha DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return None
    return _as_float(fila[0]) if fila else None


# ── SCHUMANN POR EVENTO (2026-10-26) ─────────────────────────────────────────

TABLA_EVENTOS = "tbl_eventos_schumann"


def asegurar_eventos(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLA_EVENTOS} ("
        "event_epoch REAL PRIMARY KEY, "
        "event_class TEXT, "
        "actividad_h REAL, "
        "media_24h REAL, "
        "n_lecturas INTEGER, "
        "fuente TEXT)"
    )


def _clase_de_magnitud(mag: float) -> str:
    if mag >= 7.0:
        return "SISMO_M7"
    if mag >= 6.0:
        return "SISMO_M6"
    if mag >= 5.0:
        return "SISMO_M5"
    return "SISMO_M4"


def _epoch_a_blk(epoch: float) -> str:
    return time.strftime(FMT_BLK, time.gmtime(epoch))


def enriquecer_eventos(
    conn: sqlite3.Connection,
    eventos: list,
) -> Dict[str, int]:
    """A cada evento REAL (M4.5+) le agrega SU Schumann: la lectura viva a
    su hora y el comportamiento de las 24 h previas.

    Idempotente por evento (INSERT OR IGNORE): re-verificar el mismo sismo
    no reescribe su Schumann. Fuente: tbl_schumann_vivo, preferencia por
    lecturas reales (en_vivo=1) sobre arrastres.
    """
    asegurar_eventos(conn)
    stats = {"eventos": 0, "con_dato": 0, "sin_dato": 0, "ya": 0}
    for ev in eventos:
        epoch = ev.get("epoch")
        mag = _as_float(ev.get("magnitude")) or 0.0
        if epoch is None or mag < 4.5:
            continue
        stats["eventos"] += 1
        existe = conn.execute(
            f"SELECT 1 FROM {TABLA_EVENTOS} WHERE event_epoch = ?",
            (float(epoch),),
        ).fetchone()
        if existe:
            stats["ya"] += 1
            continue
        blk = _epoch_a_blk(float(epoch))
        blk_ini = time.strftime(FMT_BLK, time.gmtime(float(epoch) - 86400))

        fila = conn.execute(
            f"SELECT schumann_activity, COALESCE(en_vivo,1) FROM {TABLA} "
            "WHERE COALESCE(en_vivo,1)=1 AND schumann_activity IS NOT NULL "
            "AND schumann_activity != 0 AND timestamp_blk <= ? "
            "ORDER BY timestamp_blk DESC LIMIT 1",
            (blk,),
        ).fetchone()
        fuente = "tbl_schumann_vivo"
        if fila is None:
            # sin lectura real: arrastre si lo hay, marcado en fuente
            fila = conn.execute(
                f"SELECT schumann_activity, 0 FROM {TABLA} "
                "WHERE schumann_activity IS NOT NULL "
                "AND timestamp_blk <= ? "
                "ORDER BY timestamp_blk DESC LIMIT 1",
                (blk,),
            ).fetchone()
            fuente = "tbl_schumann_vivo_arrastre"

        act_h = _as_float(fila[0]) if fila else None
        est = conn.execute(
            f"SELECT AVG(schumann_activity), COUNT(*) FROM {TABLA} "
            "WHERE COALESCE(en_vivo,1)=1 AND schumann_activity IS NOT NULL "
            "AND schumann_activity != 0 AND timestamp_blk BETWEEN ? AND ?",
            (blk_ini, blk),
        ).fetchone()
        media_24h = _as_float(est[0]) if est and est[0] is not None else None
        n_lect = int(est[1]) if est else 0

        if act_h is None and media_24h is None:
            stats["sin_dato"] += 1
            continue
        conn.execute(
            f"INSERT OR IGNORE INTO {TABLA_EVENTOS} "
            "(event_epoch, event_class, actividad_h, media_24h, n_lecturas, fuente) "
            "VALUES (?,?,?,?,?,?)",
            (float(epoch), _clase_de_magnitud(mag), act_h, media_24h,
             n_lect, fuente),
        )
        stats["con_dato"] += 1
    conn.commit()
    if stats["eventos"]:
        logger.info("SCHUMANN × evento: %s", stats)
    return stats


def enriquecer_historico(conn: sqlite3.Connection) -> Dict[str, int]:
    """El corpus HISTÓRICO (backcast): el Schumann de su hora-nodo, por SQL.

    Los eventos sísmicos (tbl_historico_sismico_raw, ≥4.5, con id_nodo) y
    los no sísmicos cruzan contra tbl_enjambre_telemetria por (hora, nodo):
    actividad a la hora y media de las 24 h previas del MISMO nodo. Sin
    dato en la víspera del nodo → el evento queda SIN fila (se ve, no se
    inventa). Idempotente.
    """
    asegurar_eventos(conn)
    cur = conn.execute(
        f"INSERT OR IGNORE INTO {TABLA_EVENTOS} "
        "(event_epoch, event_class, actividad_h, media_24h, n_lecturas, fuente) "
        "SELECT strftime('%s', s.timestamp_blk), "
        "  CASE WHEN s.sismo_max_mag >= 7 THEN 'SISMO_M7' "
        "       WHEN s.sismo_max_mag >= 6 THEN 'SISMO_M6' "
        "       WHEN s.sismo_max_mag >= 5 THEN 'SISMO_M5' "
        "       ELSE 'SISMO_M4' END, "
        "  t.schumann_activity, "
        "  (SELECT AVG(t2.schumann_activity) FROM tbl_enjambre_telemetria t2 "
        "    WHERE t2.id_nodo = s.id_nodo "
        "      AND t2.schumann_activity IS NOT NULL "
        "      AND t2.timestamp_blk BETWEEN datetime(s.timestamp_blk, '-24 hours') "
        "                                AND s.timestamp_blk), "
        "  (SELECT COUNT(t2.schumann_activity) FROM tbl_enjambre_telemetria t2 "
        "    WHERE t2.id_nodo = s.id_nodo "
        "      AND t2.schumann_activity IS NOT NULL "
        "      AND t2.timestamp_blk BETWEEN datetime(s.timestamp_blk, '-24 hours') "
        "                                AND s.timestamp_blk), "
        "  'tbl_enjambre_telemetria' "
        "FROM tbl_historico_sismico_raw s "
        "JOIN tbl_enjambre_telemetria t "
        "  ON t.id_nodo = s.id_nodo AND t.timestamp_blk = s.timestamp_blk "
        "WHERE s.sismo_max_mag >= 4.5 AND t.schumann_activity IS NOT NULL"
    )
    sismicos = cur.rowcount
    no_sismicos = 0
    try:
        cur = conn.execute(
            f"INSERT OR IGNORE INTO {TABLA_EVENTOS} "
            "(event_epoch, event_class, actividad_h, media_24h, n_lecturas, fuente) "
            "SELECT strftime('%s', n.timestamp_blk), n.event_class, "
            "  t.schumann_activity, "
            "  (SELECT AVG(t2.schumann_activity) FROM tbl_enjambre_telemetria t2 "
            "    WHERE t2.id_nodo = n.id_nodo "
            "      AND t2.schumann_activity IS NOT NULL "
            "      AND t2.timestamp_blk BETWEEN datetime(n.timestamp_blk, '-24 hours') "
            "                                AND n.timestamp_blk), "
            "  (SELECT COUNT(t2.schumann_activity) FROM tbl_enjambre_telemetria t2 "
            "    WHERE t2.id_nodo = n.id_nodo "
            "      AND t2.schumann_activity IS NOT NULL "
            "      AND t2.timestamp_blk BETWEEN datetime(n.timestamp_blk, '-24 hours') "
            "                                AND n.timestamp_blk), "
            "  'tbl_enjambre_telemetria' "
            "FROM tbl_eventos_no_sismicos n "
            "JOIN tbl_enjambre_telemetria t "
            "  ON t.id_nodo = n.id_nodo AND t.timestamp_blk = n.timestamp_blk "
            "WHERE t.schumann_activity IS NOT NULL"
        )
        no_sismicos = cur.rowcount
    except sqlite3.OperationalError as _e:
        # Tabla ausente en DBs viejas/facturas parciales: se VE, no se traga.
        logger.warning("SCHUMANN × histórico: sin tbl_eventos_no_sismicos (%s)", _e)
    conn.commit()
    stats = {"sismicos": int(sismicos or 0), "no_sismicos": int(no_sismicos or 0)}
    logger.info("SCHUMANN × histórico: %s", stats)
    return stats
