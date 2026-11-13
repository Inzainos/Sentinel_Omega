"""
Sentinel Omega — SQLite Schema & Migrations (v11, self-expanding)

Full DDL lives in schema_parts/*.b64 (zlib+base64).
On import, parts are joined, decompressed, and executed in this module namespace.
"""
from __future__ import annotations

import base64
import logging
import os
import sqlite3
import zlib
from pathlib import Path
from typing import Callable, Optional, cast

logger = logging.getLogger(__name__)

_PARTS_DIR = Path(__file__).resolve().parent / "schema_parts"

def _load_expanded() -> str:
    parts = sorted(_PARTS_DIR.glob("schema_part_*.b64"))
    if not parts:
        raise RuntimeError(f"schema_parts missing under {_PARTS_DIR}")
    b64 = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    return zlib.decompress(base64.b64decode(b64)).decode("utf-8")

_src = _load_expanded()
# Parche en carga (2026-10-09): el DDL canónico trae
# `schumann_hz REAL DEFAULT 7.83` en TBL_PRECURSORES_COSMICOS — una máquina de
# fabricación en potencia: cualquier INSERT que omita la columna escribiría la
# fundamental «medida». El escritor vivo siempre la especifica (None = sin
# medir, regla 2), pero el DEFAULT es una trampa parada. Los schema_parts son
# artefactos comprimidos; el parche AQUÍ queda legible y auditable en el diff.
# Forward-only: las tablas ya creadas conservan su DEFAULT viejo (SQLite no
# permite ALTER de DEFAULT); esto corrige los checkouts nuevos.
# La frecuencia Schumann no se mide desde el retiro del 2026-10-09. Hay dos
# variantes de espaciado en el DDL expandido (medidas): una con un solo
# espacio y otra con cuatro; se parchean las dos.
_src = _src.replace(
    "schumann_hz     REAL    DEFAULT 7.83,",
    "schumann_hz     REAL,          -- sin medir = NULL; el 7.83 era fabricación",
).replace(
    "schumann_hz     REAL DEFAULT 7.83,",
    "schumann_hz     REAL,",
)
exec(compile(_src, "schema_expanded", "exec"), globals())


# NOTE:
# El módulo expandido define get_connection() como alias directo de init_database(),
# lo que vuelve a ejecutar migraciones DDL en cada conexión. Si otro proceso tiene
# write-lock (launcher vivo + watchdog/reportes), eso dispara OperationalError
# "database is locked" en llamadas de solo lectura.
#
# Aquí hacemos un wrapper resiliente: intentamos init_database() primero (camino
# normal), y si la DB está bloqueada caemos a una conexión directa con PRAGMAs de
# runtime sin DDL.
_init_database_expanded = globals().get("init_database")


# Cuánto espera una ESCRITURA VIVA por el candado, en segundos.
#
# El defecto de SQLite son 5 s, y no alcanzan. Medido el 2026-09-28 sobre el
# ciclo en producción: SEIS escrituras por ciclo se perdían con «database is
# locked» --- el LOCF de alfa1, beta1, beta2 y delta, la persistencia sísmica y
# la del clima horario --- y las seis son fail-soft, así que el ciclo terminaba
# «bien» y nadie se enteraba. La consecuencia visible: `tbl_clima_espacial_raw`
# dejó de crecer a las 02:00, las ventanas de 336 h y 72 h del Kp se congelaron
# en ese borde, y beta1 devolvió la MISMA confianza (0,3665) doce ciclos
# seguidos. El operador lo vio antes que cualquier alerta: «beta1 se refresca
# pero repite el mismo valor».
#
# La contención no es accidental: `sentinel-omega-rutinas.service` corre cada
# 15 min y tarda ~5, así que se solapa con el ciclo casi siempre.
#
# 120 s es el mismo presupuesto que ya usan los lotes (`entrenamiento.py`,
# `mantenimiento.py`). Un ciclo dura ~300 s, así que esperar cabe; perder el
# dato, no. Es la regla dura 10: un descarte silencioso esconde el fallo
# indefinidamente.
ESPERA_CANDADO_S = 120.0


def _con_espera(conn: sqlite3.Connection) -> sqlite3.Connection:
    """`busy_timeout` en la conexión, venga de donde venga.

    Se pone por PRAGMA y no por `timeout=` del `connect` porque la ruta normal
    devuelve una conexión creada dentro del esquema auto-expandido, donde no se
    puede pasar el argumento.
    """
    try:
        conn.execute(f"PRAGMA busy_timeout={int(ESPERA_CANDADO_S * 1000)}")
    except sqlite3.Error as exc:  # noqa: BLE001 — nunca bloquea el arranque
        logger.warning("No se pudo fijar busy_timeout: %s", exc)
    return conn


# Los PRAGMA de runtime que el esquema expandido ya pone en `get_connection`.
# Se repiten aquí porque los lotes NO pasan por ahí: abrir `get_connection` en
# cada función de lote reejecutaría las migraciones DDL en cada llamada, que es
# justo lo que el envoltorio resiliente de más abajo intenta evitar.
#
# Que estén en DOS sitios es una duplicación real, y la fija
# `tests/test_conexion_de_lote.py` comparando una conexión de lote contra una
# viva: si alguien cambia uno y no el otro, falla.
PRAGMAS_RUNTIME = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA cache_size=-8000",
    "PRAGMA temp_store=MEMORY",
)


def conexion_de_lote(db_path: str) -> sqlite3.Connection:
    """Conexión para TAREAS DE LOTE, con la MISMA política que la ruta viva.

    Lo que estaba roto (medido el 2026-10-02, perfilando la Fase 2)
    ---------------------------------------------------------------
    `entrenamiento.py` y `mantenimiento.py` abrían `sqlite3.connect(db_path,
    timeout=...)` a pelo, así que **se saltaban los PRAGMA del esquema** y
    heredaban los de SQLite por defecto. El que dolía:

        sqlite3.connect pelado      synchronous = 2  (FULL)
        get_connection (ruta viva)  synchronous = 1  (NORMAL, desde siempre)

    O sea: no era un canje de durabilidad que hiciera falta decidir. Los lotes
    eran accidentalmente **más** durables que el ciclo vivo, y lo pagaban con
    un `fsync` por commit.

    Lo que costaba, medido en esta máquina:

        synchronous=FULL     6,83 ms/commit
        synchronous=NORMAL   0,04 ms/commit     --- 170x

    Y los commits no son pocos. Perfil de la Fase 2:

        13.571 commits  =  207,6 s de 286,1 s  =  **73 %** del total
        4.523 evaluaciones -> 3,0 commits cada una

    Tres por evaluación, uno en cada sitio y los tres correctos ahí:
    `juez.registrar_prediccion`, `juez.evaluar_pendientes`, `pesos._ajustar`.
    Para las 140.613 evaluaciones de una Fase 2 completa son **~420.000 fsync**
    --- 48 minutos de puro disco.

    Por qué la misma tarea tardaba 14, >110 y 38 minutos
    ----------------------------------------------------
    Porque la latencia del `fsync` es lo que varía con la carga del disco: el
    dashboard leyendo 1,6 MB/s con nueve cerrojos abiertos, el `clamscan` del
    watchdog cada hora en punto. El trabajo era idéntico (140.800 contra
    140.613 evaluaciones, 0,1 %). Se descartaron por medición la E/S del
    proceso, la competencia de CPU y las estadísticas rancias de `sqlite_stat1`
    --- el plan de `Juez.reincidencia` seguía siendo el correcto y tardaba
    0,03 ms. Era el disco, dentro del commit.

    A/B con el código real sobre la misma copia limpia: **286,1 s -> 74,1 s**.
    """
    conn = sqlite3.connect(db_path, timeout=ESPERA_CANDADO_S)
    _con_espera(conn)
    for pragma in PRAGMAS_RUNTIME:
        try:
            conn.execute(pragma)
        except sqlite3.Error as exc:  # noqa: BLE001 — el lote corre igual
            logger.warning("No se pudo aplicar %s: %s", pragma, exc)
    return conn


# D3 / G-2 (P1, 2026-11-10): init_database() re-ejecutaba TODO el DDL +
# migraciones + DROP/CREATE VIEW en CADA conexión, y get_connection()
# ignoraba SENTINEL_DB. Este envoltorio es el init_database que ven los
# importadores (launcher, repositorio): si la DB ya está en versión 11,
# NO toca DDL/vistas/migraciones y devuelve una conexión con los PRAGMA
# de runtime. Si no está en 11 (o no existe), delega al init expandido,
# que crea/migra como antes. OJO: un cambio de esquema futuro DEBE subir
# SCHEMA_VERSION, o este atajo lo saltará.
def _version_esquema(path: Path) -> Optional[int]:
    """MAX(version) de TBL_SCHEMA_VERSION sin crear ni escribir nada.

    Devuelve None si el archivo no existe o la tabla no está (DB nueva o
    anterior a v11): en esos casos el init completo debe correr.
    """
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            fila = conn.execute(
                "SELECT MAX(version) FROM TBL_SCHEMA_VERSION"
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not fila or fila[0] is None:
        return None
    return int(fila[0])


def init_database(db_path: str) -> sqlite3.Connection:
    """Inicializa la DB; no-op de DDL si ya está en SCHEMA_VERSION.

    Reemplaza al init_database() expandido para quien importa este módulo
    (el expandido sigue en _init_database_expanded para el camino de
    creación/migración).
    """
    path = Path(db_path)
    version = _version_esquema(path)
    if version is not None and version >= int(globals().get("SCHEMA_VERSION", 11)):
        logger.info("DB %s ya en esquema v%s: sin DDL", db_path, version)
        conn = sqlite3.connect(str(path), timeout=ESPERA_CANDADO_S)
        for pragma in PRAGMAS_RUNTIME:
            try:
                conn.execute(pragma)
            except sqlite3.Error as exc:  # noqa: BLE001 — el lote corre igual
                logger.warning("No se pudo aplicar %s: %s", pragma, exc)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.Error as exc:  # noqa: BLE001
            logger.warning("No se pudo aplicar foreign_keys: %s", exc)
        return _con_espera(conn)
    if not callable(_init_database_expanded):
        raise RuntimeError("init_database no disponible tras expandir schema")
    init_fn = cast(Callable[[str], sqlite3.Connection], _init_database_expanded)
    return _con_espera(init_fn(db_path))


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get DB connection with lock-tolerant fallback.

    1) Prefer init_database() to keep forward-only migrations.
    2) If DB is temporarily write-locked, open direct connection and continue.

    D3 (P1, 2026-11-10): SENTINEL_DB gana sobre el default del checkout
    (antes se ignoraba y la suite escribía la DB de producción).
    """
    if db_path is None:
        db_path = os.environ.get("SENTINEL_DB") or str(
            Path(__file__).parent.parent.parent / "data" / "SENTINEL_OMEGA_PRO.db"
        )
    try:
        return init_database(db_path)
    except sqlite3.OperationalError as exc:
        if "locked" not in str(exc).lower():
            raise
        logger.warning(
            "DB lock detectado en init_database(%s); usando conexión directa sin DDL",
            db_path,
        )
        conn = sqlite3.connect(str(db_path), timeout=ESPERA_CANDADO_S)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return _con_espera(conn)
