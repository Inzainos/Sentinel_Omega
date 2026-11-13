"""Helpers para consulta de biblioteca cimática en modo lectura.

Este módulo se usa por el dashboard (/api/cimatica/ahora).
No inventa datos: si la biblioteca no existe o está vacía, consulta
contra tbl_cimatica_patrones como fallback de similitud por clave.

construir_biblioteca (2026-10-25) es el POBLADOR: deriva la biblioteca
de los eventos históricos con la misma extracción que el entrenamiento
cimático, para que vísperas históricas y figura viva hablen el mismo
idioma (mismas claves) y la comparación sea real.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .cimatica import clave_patron

logger = logging.getLogger(__name__)

# Caché del lookup de biblioteca (ver consultar): una entrada por clave
# viva + tamaño de biblioteca; se limpia sola a 8 entradas.
_CONSULTA_CACHE: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return bool(row)


def ensure_biblioteca(conn: sqlite3.Connection) -> None:
    """Crea tabla de biblioteca cuando la conexión es writable.

    En dashboard RO esto puede fallar (expected) y el caller debe tolerarlo.

    El índice ÚNICO (clave_figura, event_class) es lo que hace posible el
    upsert del integrador por evento (integrar_evento_biblioteca). Si la
    tabla existiera con duplicados (nunca tras construir_biblioteca, que
    agrega), el índice falla y se LOGUEA — no se traga en silencio (regla
    10) — y el integrador queda deshabilitado hasta reconstruir.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tbl_cimatica_biblioteca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave_figura TEXT,
            event_class TEXT,
            n_eventos INTEGER DEFAULT 0,
            figura_json TEXT,
            factores_json TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_cimatica_bib_clave_clase "
            "ON tbl_cimatica_biblioteca(clave_figura, event_class)"
        )
    except sqlite3.Error as e:
        logger.warning(
            "BIBLIOTECA: índice único (clave, clase) no creado — hay "
            "duplicados y el integrador por evento queda inerte: %s", e,
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cimatica_bib_clave ON tbl_cimatica_biblioteca(clave_figura)"
    )


def _norm(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _items_from_dict(d: Dict[str, Any]) -> List[Tuple[str, float]]:
    out: List[Tuple[str, float]] = []
    for k, v in sorted((d or {}).items()):
        if isinstance(v, (int, float)):
            out.append((str(k), _norm(v)))
    return out


def _similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """Similitud simple [0..1] sobre features numéricas compartidas."""
    ia = dict(_items_from_dict(a))
    ib = dict(_items_from_dict(b))
    if not ia and not ib:
        return 0.0
    keys = sorted(set(ia.keys()) | set(ib.keys()))
    if not keys:
        return 0.0
    score = 0.0
    for k in keys:
        va = ia.get(k, 0.0)
        vb = ib.get(k, 0.0)
        den = abs(va) + abs(vb) + 1e-9
        score += max(0.0, 1.0 - abs(va - vb) / den)
    return round(score / len(keys), 4)


def _load_pattern_rows(conn: sqlite3.Connection, limit: int = 250) -> Iterable[sqlite3.Row]:
    if not _table_exists(conn, "tbl_cimatica_patrones"):
        return []
    return conn.execute(
        """
        SELECT patron_id, clave, ambito, id_nodo, event_class, frecuencia,
               primera_vez, ultima_vez, telemetria_json
        FROM tbl_cimatica_patrones
        ORDER BY ultima_vez DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def consultar(
    conn: sqlite3.Connection,
    figura: Dict[str, Any],
    factores: Dict[str, Any],
    clave_figura: str = "",
) -> Dict[str, Any]:
    """Busca similares de manera robusta.

    Prioridad:
    1) coincidencias en tbl_cimatica_biblioteca (si existe y hay filas)
    2) fallback en tbl_cimatica_patrones por similitud de telemetría
    """
    query = {**(figura or {}), **(factores or {})}
    if not clave_figura:
        try:
            clave_figura = clave_patron(query)
        except Exception:
            clave_figura = ""

    similares: List[Dict[str, Any]] = []

    # 1) Biblioteca explícita — escaneo completo con caché (ver
    # _scan_biblioteca: el LIMIT 300 original moría a escala real y el
    # lookup daba 0 hits SIEMPRE — medido 2026-10-25).
    if _table_exists(conn, "tbl_cimatica_biblioteca"):
        similares.extend(_scan_biblioteca(conn, clave_figura))

    # 2) Fallback patrones
    if not similares:
        for r in _load_pattern_rows(conn, limit=500):
            row_features: Dict[str, Any] = {}
            txt = r["telemetria_json"]
            if isinstance(txt, str) and txt.strip().startswith("{"):
                import json

                try:
                    row_features = json.loads(txt)
                except Exception:
                    row_features = {}
            sim = 0.0
            if row_features and query:
                sim = _similarity(query, row_features)
            elif clave_figura:
                rk = str(r["clave"] or "")
                if rk:
                    a = set(clave_figura.split("|"))
                    b = set(rk.split("|"))
                    inter = len(a & b)
                    union = max(1, len(a | b))
                    sim = round(inter / union, 4)
            if sim <= 0:
                continue
            similares.append(
                {
                    "source": "tbl_cimatica_patrones",
                    "patron_id": r["patron_id"],
                    "clave": r["clave"],
                    "ambito": r["ambito"],
                    "id_nodo": r["id_nodo"],
                    "event_class": r["event_class"],
                    "frecuencia": int(r["frecuencia"] or 0),
                    "ultima_vez": r["ultima_vez"],
                    "similarity": sim,
                }
            )

    similares.sort(key=lambda x: (float(x.get("similarity") or 0.0), int(x.get("frecuencia") or x.get("n_eventos") or 0)), reverse=True)
    similares = similares[:20]
    best = float(similares[0]["similarity"]) if similares else 0.0

    return {
        "similares": similares,
        "n_hits": len(similares),
        "best_similarity": best,
        "live_train": False,
    }


# ── POBLADOR (2026-10-25) ────────────────────────────────────────────────────


def construir_biblioteca(
    conn: sqlite3.Connection,
    max_eventos: Optional[int] = None,
    log_cada: int = 10_000,
) -> Dict[str, int]:
    """Puebla tbl_cimatica_biblioteca: vísperas etiquetadas comparables.

    Para cada evento histórico (sísmicos >= MIN_MAGNITUD_OBSERVAR + no
    sísmicos) extrae las features de su víspera con la MISMA extracción que
    entrenar_cimatica (extraer_features_ventana) y agrega por figura:

        (clave_figura, event_class) -> n_eventos = eventos CUYA víspera
                                        produjo esa clave
        figura_json = telemetría de la última víspera con esa clave

    n_eventos cuenta EVENTOS, no avistamientos: la `frecuencia` de
    tbl_cimatica_patrones mezcla vísperas de entrenamiento con recurrencias
    vivas sin evento, y usarla aquí contaría calma como víspera (regla 11:
    un número medido solo sobre eventos no mide nada). La biblioteca es
    DESCRIPTIVA — qué figuras antecedieron a qué eventos —; el lift frente
    a calma lo mide el Juez, no esta tabla.

    La figura es DETERMINISTA (clave → misma figura, como las placas de
    Chladni): la misma telemetría siempre produce la misma clave, así que
    la comparación viva contra la biblioteca es real, no aproximada.

    Idempotente: reconstruye la tabla completa en cada corrida (la tabla es
    DERIVADA de los eventos; borrarla y reinsertar es el único estado
    consistente). `conn` debe ser WRITABLE — el dashboard RO nunca llama
    aquí; por eso `ensure_biblioteca` tolera fallar allá.
    """
    from sentinel_omega.core.firmas.signature_engine import (
        extraer_features_ventana,
    )
    from sentinel_omega.infrastructure.pipeline.entrenamiento import (
        MIN_MAGNITUD_OBSERVAR, _event_class,
    )

    eventos = conn.execute(
        "SELECT timestamp_blk, id_nodo, sismo_max_mag "
        "FROM tbl_historico_sismico_raw WHERE sismo_max_mag >= ? "
        "ORDER BY timestamp_blk",
        (MIN_MAGNITUD_OBSERVAR,),
    ).fetchall()
    no_sismicos: List[Tuple[Any, ...]] = []
    try:
        no_sismicos = conn.execute(
            "SELECT timestamp_blk, id_nodo, event_class "
            "FROM tbl_eventos_no_sismicos ORDER BY timestamp_blk"
        ).fetchall()
    except sqlite3.OperationalError:
        logger.warning(
            "BIBLIOTECA: tbl_eventos_no_sismicos ausente — sólo sismos"
        )
    if max_eventos:
        eventos = eventos[:max_eventos]

    stats = {
        "eventos": 0, "sin_datos": 0, "vísperas": 0,
        "figuras": 0, "filas": 0,
    }
    logger.info(
        f"=== BIBLIOTECA CIMÁTICA: {len(eventos)} sísmicos + "
        f"{len(no_sismicos)} no sísmicos ==="
    )

    # (clave, clase) -> [n_eventos, figura de la última víspera]
    agg: Dict[Tuple[str, str], List[Any]] = {}

    def _víspera(ts, id_nodo, clase):
        features = extraer_features_ventana(conn, ts, id_nodo)
        if features is None:
            stats["sin_datos"] += 1
            return
        stats["vísperas"] += 1
        clave = clave_patron(features)
        if not clave:
            return
        k = (clave, clase)
        fila = agg.get(k)
        if fila is None:
            agg[k] = [1, features]
        else:
            fila[0] += 1
            fila[1] = features

    for ts, id_nodo, mag in eventos:
        _víspera(ts, id_nodo, _event_class(mag))
        stats["eventos"] += 1
        if stats["eventos"] % log_cada == 0:
            logger.info(
                f"  Biblioteca: {stats['eventos']} eventos — "
                f"{len(agg)} figuras, {stats['sin_datos']} sin datos"
            )
    for ts, id_nodo, clase in no_sismicos:
        _víspera(ts, id_nodo, str(clase))
        stats["eventos"] += 1

    ensure_biblioteca(conn)
    conn.execute("DELETE FROM tbl_cimatica_biblioteca")
    conn.executemany(
        "INSERT INTO tbl_cimatica_biblioteca "
        "(clave_figura, event_class, n_eventos, figura_json) "
        "VALUES (?, ?, ?, ?)",
        [
            (clave, clase, n, json.dumps(figura, default=float))
            for (clave, clase), (n, figura) in agg.items()
        ],
    )
    # Re-asegura DESPUÉS del DELETE+INSERT: si la tabla venía con duplicados
    # de una build vieja, el índice único falló en el primer ensure y aquí
    # ya encuentra la tabla limpia (la agregación no produce duplicados).
    ensure_biblioteca(conn)
    conn.commit()
    stats["figuras"] = len(agg)
    stats["filas"] = conn.execute(
        "SELECT COUNT(*) FROM tbl_cimatica_biblioteca"
    ).fetchone()[0]
    logger.info(f"Biblioteca cimática construida: {stats}")
    return stats


# ── EVIDENCIA CIMÁTICA PARA EL PADRE (2026-10-25) ─────────────────────────────
#
# Calibración medida contra el nulo ANTES de cablear (regla 9/11),
# deploy/medir_cimatica_evidencia.py, 147 vísperas (LOO) vs 44 calmas:
#
#   umbral   vísperas   calma   ganancia
#   0.70     100.0%    95.5%    1.05x
#   0.80      87.8%    77.3%    1.14x
#   0.90      49.0%    40.9%    1.20x
#   0.95      12.2%    15.9%    0.77x   ← invertido
#   1.00       0.0%    15.9%    0.00x   ← la CALMA empareja MÁS
#
# La semejanza (y hasta la IDENTIDAD) de figura NO distingue víspera de
# calma: el espacio de claves por bandas es denso y las mismas figuras
# recurren en calma. Por eso esto es EVIDENCIA con etiqueta honesta —
# CONTEXTO, nunca compuerta ni umbral de decisión (misma disciplina que
# el tono espectral, audit 2026-10-21).
CALIBRACION_EVIDENCIA = {
    "n_vísperas": 147, "n_calma": 44,
    "calma_mediana_sim": 0.868, "calma_match_exacto": 0.159,
    "ganancia_max_medida": 1.20,
    "nota": ("la calma empareja igual o más que la víspera; contexto, "
             "no predicción"),
}


def _scan_biblioteca(conn: sqlite3.Connection, clave_figura: str) -> List[Dict[str, Any]]:
    """Mejores matches de la clave contra la biblioteca, con caché.

    Es el escaneo completo medido (~3 s primera vez por clave; la clave
    viva solo cambia cada ciclo), compartido por consultar() y
    cimatica_evidencia().
    """
    n_lib = int(
        conn.execute(
            "SELECT COUNT(*) FROM tbl_cimatica_biblioteca"
        ).fetchone()[0] or 0
    )
    cache_key: Tuple[str, int] = (clave_figura, n_lib)
    encontrados = _CONSULTA_CACHE.get(cache_key)
    if encontrados is not None:
        return encontrados
    a = set(clave_figura.split("|")) if clave_figura else set()
    encontrados = []
    # Acceso POSICIONAL: el SELECT lo controla este módulo, y la conexión
    # del launcher viene SIN row_factory (tuplas) — la del dashboard usa
    # sqlite3.Row. Por nombre reventaba en el launcher (medido 2026-10-26:
    # «tuple indices must be integers or slices, not str»).
    for clave_b, clase_b, n_ev, upd in conn.execute(
        "SELECT clave_figura, event_class, n_eventos, updated_at "
        "FROM tbl_cimatica_biblioteca"
    ).fetchall():
        k = str(clave_b or "")
        if not k or not clave_figura:
            continue
        if k == clave_figura:
            sim = 1.0
        elif a:
            b = set(k.split("|"))
            inter = len(a & b)
            if not inter:
                continue
            sim = round(inter / max(1, len(a | b)), 4)
        else:
            continue
        encontrados.append(
            {
                "source": "tbl_cimatica_biblioteca",
                "clave": k,
                "event_class": clase_b,
                "n_eventos": int(n_ev or 0),
                "similarity": sim,
                "updated_at": upd,
            }
        )
    encontrados.sort(
        key=lambda x: (x["similarity"], x["n_eventos"]), reverse=True
    )
    encontrados = encontrados[:20]
    _CONSULTA_CACHE[cache_key] = encontrados
    if len(_CONSULTA_CACHE) > 8:
        _CONSULTA_CACHE.pop(next(iter(_CONSULTA_CACHE)))
    return encontrados


def cimatica_evidencia(
    conn: sqlite3.Connection,
    features: Dict[str, Any],
) -> Dict[str, Any]:
    """El filtro cimático del Padre: qué vísperas históricas empareja la
    figura viva (idéntica o similar), con el nulo pegado al número.

    EVIDENCIA, no compuerta: la calibración (arriba) mostró que la calma
    empareja igual o más que la víspera — el dict lleva la etiqueta para
    que ningún consumidor lo lea como predicción.
    """
    if not _table_exists(conn, "tbl_cimatica_biblioteca"):
        return {"presente": False, "resumen": "biblioteca no construida"}
    clave = clave_patron(features) if features else ""
    if not clave:
        return {"presente": True, "match_exacto": False, "mejor_sim": 0.0,
                "top": [], "calibracion": CALIBRACION_EVIDENCIA,
                "resumen": "sin clave de telemetría"}
    similares = _scan_biblioteca(conn, clave)
    if not similares:
        return {"presente": True, "match_exacto": False, "mejor_sim": 0.0,
                "top": [], "calibracion": CALIBRACION_EVIDENCIA,
                "resumen": "sin emparejes"}
    top = [
        {"clase": s["event_class"], "n_eventos": s["n_eventos"],
         "sim": s["similarity"]}
        for s in similares[:3]
    ]
    mejor = similares[0]
    exacto = mejor["similarity"] >= 1.0
    if exacto:
        resumen = (
            f"figura viva IDÉNTICA a la víspera de {mejor['n_eventos']}×"
            f"{mejor['event_class']} — CONTEXTO: la calma empareja igual "
            f"(match exacto en {CALIBRACION_EVIDENCIA['calma_match_exacto']:.0%} "
            "de calmas medidas), no es predicción"
        )
    else:
        resumen = (
            f"figura viva similar {mejor['similarity']:.2f} a víspera de "
            f"{mejor['event_class']} (n={mejor['n_eventos']}) — CONTEXTO, "
            "no predicción (ganancia medida ≤1.2×)"
        )
    return {
        "presente": True,
        "match_exacto": exacto,
        "mejor_sim": mejor["similarity"],
        "mejor_clase": mejor["event_class"],
        "mejor_n_eventos": mejor["n_eventos"],
        "top": top,
        "calibracion": CALIBRACION_EVIDENCIA,
        "resumen": resumen,
    }


# ── INTEGRADOR POR EVENTO (2026-10-25) ────────────────────────────────────────

# Ventana de víspera para integrar (h) — la MISMA de
# cimatica.retroetiquetar_patrones, para que etiqueta e integración lean
# la misma ventana.
VISPERA_INTEGRAR_H = 72


def integrar_evento_biblioteca(
    conn: sqlite3.Connection,
    eventos: List[Dict[str, Any]],
    ventana_h: int = VISPERA_INTEGRAR_H,
) -> Dict[str, int]:
    """Integra a la biblioteca la figura cimática de cada evento REAL vivo.

    «Por evento se integraría de igual forma su figura»: cuando el Juez
    verifica un evento M4.5+, las figuras que estuvieron vivas en su
    víspera ya quedaron etiquetadas en tbl_cimatica_patrones
    (retroetiquetar_patrones); aquí cruzan a la biblioteca con el conteo
    honesto — n_eventos+1 POR EVENTO Y POR FIGURA, deduplicadas dentro
    del evento (un evento con la misma clave en general y en nodo cuenta
    UNO, no dos).

    Idempotente por EPISODIO: tbl_cimatica_bib_eventos guarda el epoch de
    cada sismo ya integrado — el Juez puede verificar el mismo catálogo en
    corridas superpuestas sin inflar el conteo.
    """
    from datetime import datetime, timezone

    stats = {"eventos": 0, "integrados": 0, "figuras": 0, "sin_patron": 0,
             "ya_integrados": 0}
    if not _table_exists(conn, "tbl_cimatica_patrones"):
        return stats
    ensure_biblioteca(conn)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tbl_cimatica_bib_eventos ("
        "event_epoch REAL PRIMARY KEY, event_class TEXT, "
        "integrado_at TEXT DEFAULT (datetime('now')))"
    )
    for ev in eventos:
        epoch = ev.get("epoch")
        mag = ev.get("magnitude") or 0.0
        if epoch is None or mag < 4.5:
            continue
        stats["eventos"] += 1
        clase = f"SISMO_M{int(mag)}" if mag < 7 else "SISMO_M7"
        cur = conn.execute(
            "INSERT OR IGNORE INTO tbl_cimatica_bib_eventos "
            "(event_epoch, event_class) VALUES (?, ?)",
            (float(epoch), clase),
        )
        if cur.rowcount == 0:
            stats["ya_integrados"] += 1
            continue
        ini = datetime.fromtimestamp(
            epoch - ventana_h * 3600, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")
        fin = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S")
        # Figuras de la víspera de ESTE evento: patrones etiquetados con
        # esta clase cuya última aparición cayó en la ventana. Dedup por
        # clave DENTRO del evento.
        filas = conn.execute(
            "SELECT DISTINCT clave, telemetria_json "
            "FROM tbl_cimatica_patrones "
            "WHERE event_class = ? AND ultima_vez BETWEEN ? AND ?",
            (clase, ini, fin),
        ).fetchall()
        if not filas:
            stats["sin_patron"] += 1
        nuevas = 0
        for clave, tel in filas:
            try:
                conn.execute(
                    "INSERT INTO tbl_cimatica_biblioteca "
                    "(clave_figura, event_class, n_eventos, figura_json) "
                    "VALUES (?, ?, 1, ?) "
                    "ON CONFLICT(clave_figura, event_class) DO UPDATE SET "
                    "n_eventos = n_eventos + 1, updated_at = datetime('now')",
                    (clave, clase, tel or "{}"),
                )
                nuevas += 1
            except sqlite3.Error as e:
                logger.warning(
                    "BIBLIOTECA: upsert de evento falló (¿índice único "
                    "ausente por duplicados? reconstruir con "
                    "construir_biblioteca): %s", e,
                )
                break
        stats["figuras"] += nuevas
        stats["integrados"] += 1
    conn.commit()
    if stats["integrados"] or stats["ya_integrados"]:
        logger.info(
            "BIBLIOTECA × evento: %s integrados (%s figuras) · %s ya "
            "integrados · %s sin patrón en víspera",
            stats["integrados"], stats["figuras"], stats["ya_integrados"],
            stats["sin_patron"],
        )
    return stats
