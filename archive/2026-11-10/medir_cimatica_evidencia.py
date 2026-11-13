"""Medición de la evidencia cimática para el Padre — vísperas vs calma.

La pregunta del operador: «integrarle al padre ese filtro cimático en caso
de encontrar una figura idéntica al pasado o similar». La regla dura 9/11
del proyecto exige calibrar ANTES de cablear: ¿qué significa que la figura
viva se parezca a una víspera de evento? Solo si esa semejanza distingue
vísperas de CALMA significa algo; si calma también empareja, es ruido con
cara de señal (el vicio medido del tono: 94% «volcánico» en vísperas
sísmicas leyendo el RÉGIMEN de clima espacial).

Diseño (espejo del audit de la tela, 2026-10-21):
  - VÍSPERAS: muestra estratificada M4.5+ + no sísmicos. best_sim contra la
    biblioteca CON leave-one-out: se excluyen las filas con la MISMA clave
    de la propia víspera (emparejar consigo misma es trivial).
  - CALMA: mismas horas-nodo de las vísperas desplazadas +14 d, aceptadas
    sólo si el nodo no tiene bloque M≥2.5 en ±7 d. best_sim sin exclusión.
  - NULO: la tasa de empareje de la calma a cada umbral — la vara contra
    la que se lee cualquier «hallazgo».

Salida: distribución por grupo, tasas por umbral, ganancia (Molchan-style:
tasa_vísperas / tasa_calma) y el umbral recomendado si hay separación.

Uso:
    .venv/bin/python deploy/medir_cimatica_evidencia.py [db_path] [--n 150]
"""
from __future__ import annotations

import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from random import Random

DB_DEFAULT = "sentinel_omega/data/SENTINEL_OMEGA_PRO.db"

UMBRALES = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]


def _jaccard(a: frozenset, b: set) -> float:
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(raiz))

    n_muestra = 150
    if "--n" in sys.argv:
        n_muestra = int(sys.argv[sys.argv.index("--n") + 1])
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    db_path = Path(args[0]) if args else raiz / DB_DEFAULT
    if not db_path.is_file():
        print(f"DB no encontrada: {db_path}")
        return 2

    from sentinel_omega.core.firmas.cimatica import clave_patron
    from sentinel_omega.core.firmas.signature_engine import extraer_features_ventana

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    # ── Biblioteca en memoria (una sola lectura, ~177k claves) ──────────
    t0 = time.time()
    bib = [r[0] for r in conn.execute(
        "SELECT clave_figura FROM tbl_cimatica_biblioteca"
    ).fetchall() if r[0]]
    bib_sets = [set(c.split("|")) for c in bib]
    print(f"Biblioteca: {len(bib)} figuras cargadas ({time.time()-t0:.1f}s)")

    rng = Random(20261025)

    # ── Vísperas: estratificadas por clase M4.5+ + no sísmicos ───────────
    clases = [("SISMO_M4", 4.5, 5.0), ("SISMO_M5", 5.0, 6.0),
              ("SISMO_M6", 6.0, 7.0), ("SISMO_M7", 7.0, 10.0)]
    eves = []
    por_clase = max(10, n_muestra // (len(clases) + 1))
    for clase, lo, hi in clases:
        filas = conn.execute(
            "SELECT timestamp_blk, id_nodo FROM tbl_historico_sismico_raw "
            "WHERE sismo_max_mag >= ? AND sismo_max_mag < ? "
            "ORDER BY RANDOM() LIMIT ?",
            (lo, hi, por_clase),
        ).fetchall()
        eves.extend((ts, nodo, clase) for ts, nodo in filas)
    ns = conn.execute(
        "SELECT timestamp_blk, id_nodo, event_class FROM tbl_eventos_no_sismicos "
        "ORDER BY RANDOM() LIMIT ?", (por_clase,),
    ).fetchall()
    eves.extend((ts, nodo, cl) for ts, nodo, cl in ns)
    rng.shuffle(eves)
    eves = eves[: n_muestra * 2]

    # ── Calma: primera hora +14/+21/+28/+35 d con nodo sin M≥2.5 en ±7 d ─
    from datetime import datetime, timedelta
    calm = []
    for ts, nodo, _ in eves:
        base = datetime.strptime(ts, "%Y-%m-%d %H:%M")
        for dias in (14, 21, 28, 35, 42):
            c_ts = (base + timedelta(days=dias)).strftime("%Y-%m-%d %H:%M")
            ini = (base + timedelta(days=dias - 7)).strftime("%Y-%m-%d %H:%M")
            fin = (base + timedelta(days=dias + 7)).strftime("%Y-%m-%d %H:%M")
            n_ev = conn.execute(
                "SELECT COUNT(*) FROM tbl_historico_sismico_raw "
                "WHERE id_nodo = ? AND timestamp_blk BETWEEN ? AND ?",
                (nodo, ini, fin),
            ).fetchone()[0]
            if n_ev == 0:
                calm.append((c_ts, nodo))
                break
    rng.shuffle(calm)
    calm = calm[: n_muestra * 2]

    def best_sim(clave: str, excluir_propia: bool):
        a = set(clave.split("|"))
        best = 0.0
        for bs in bib_sets:
            if excluir_propia and bs == a:
                continue
            s = _jaccard(a, bs)
            if s > best:
                best = s
        return best

    def medir(muestra, es_víspera: bool):
        sims, sin_dato = [], 0
        t0 = time.time()
        for i, item in enumerate(muestra):
            ts, nodo = item[0], item[1]
            f = extraer_features_ventana(conn, ts, nodo)
            if f is None:
                sin_dato += 1
                continue
            sims.append(best_sim(clave_patron(f), es_víspera))
            if (i + 1) % 50 == 0:
                print(f"  {'vísperas' if es_víspera else 'calma'}: {i+1}/{len(muestra)} "
                      f"({time.time()-t0:.0f}s)", flush=True)
        return sims, sin_dato

    print(f"Midiendo {len(eves)} vísperas (LOO)…")
    sim_eve, sd_eve = medir(eves, True)
    print(f"Midiendo {len(calm)} calmas…")
    sim_calma, sd_calma = medir(calm, False)

    import numpy as np
    eve = np.array(sim_eve); calma = np.array(sim_calma)

    print("\n=== DISTRIBUCIÓN best_sim ===")
    print(f"{'':14} {'vísperas':>10} {'calma':>10}")
    print(f"{'n':14} {len(eve):>10} {len(calma):>10}   (sin dato: {sd_eve}/{sd_calma})")
    for nombre, fn in [("mediana", np.median), ("p90", lambda x: np.percentile(x, 90)),
                       ("p97", lambda x: np.percentile(x, 97)), ("máx", np.max)]:
        print(f"{nombre:14} {fn(eve):>10.3f} {fn(calma):>10.3f}")

    print("\n=== TASA DE EMPAREJE POR UMBRAL (la calma es el NULO) ===")
    print(f"{'umbral':>7} {'vísperas':>10} {'calma':>10} {'ganancia':>9}")
    for u in UMBRALES:
        te = float((eve >= u).mean()) if len(eve) else 0.0
        tc = float((calma >= u).mean()) if len(calma) else 0.0
        g = (te / tc) if tc > 0 else float("inf")
        print(f"{u:>7.2f} {te:>9.1%} {tc:>9.1%} {g:>8.2f}x")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
