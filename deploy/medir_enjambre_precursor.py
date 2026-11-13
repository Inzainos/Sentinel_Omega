"""¿La MIGRACIÓN DE ENJAMBRES (Omori difuso) cambia antes de un sismo?
La precursora sísmica con datos disponibles.

Por qué podría funcionar:
- Omori difuso: la sismicidad se mueve antes del evento principal
- Datos en tbl_enjambre_telemetria y tbl_historico_sismico_raw
- USGS ya en la DB (1994-2026)

Uso:  .venv/bin/python deploy/medir_enjambre_precursor.py <db_eventos> <db_enjambre>
                     [VENTANA_H [SEP_H [SEMILLA [EPOCA_D [TABLA]]]]]
"""

from __future__ import annotations

import argparse
import bisect
import datetime as dt
import random
import re
import sqlite3
import statistics as st
import sys

import numpy as np

# NOTA tuning P3 2026-11-10: sys.path hardcodeado eliminado (no se importa nada
# de sentinel_omega). Args con argparse (antes: sys.argv[1] sin comprobar ->
# IndexError) + --output a archivo (antes: solo stdout).
# FIX DEL BUG DE CANAL: los dos bloques inline leían siempre v = r[1]
# (schumann_hz en AMBOS canales; schumann_activity nunca se leía) y serie()
# — la versión correcta con r[j] — nunca se llamaba. Ahora ambos bloques
# llaman a serie(). _znorm estaba definida 3 veces: queda una. La consulta
# de `horas` hardcodeaba tbl_enjambre_telemetria: ahora usa TABLA.
# DATO (verificado vivo 2026-11-10): schumann_hz es NULL en 1,072/1,072 filas
# y schumann_activity solo tiene 301 valores en un año; una ventana de 336 h
# necesita >=48 filas y >=24 bins finitos por canal, así que el script sigue
# sin poder producir parejas hasta que la tabla tenga datos reales.

# Tabla de enjambres (donde están los datos de enjambres)
TABLA = "tbl_enjambre_telemetria"

# La ventana. 336 h es la de las firmas, heredada
VENTANA_H = 336
HORIZONTE_H = 190
EPOCA_D = 180
# Separacion minima entre ventanas. 336 h = el largo de la ventana
SEP_H = 336
SEMILLA = 53
N_BINS = 48

# Columnas disponibles en tbl_enjambre_telemetria
# timestamp_blk, id_nodo, schumann_hz, en_vivo, schumann_activity
CANALES = ("schumann_hz", "schumann_activity")

# Tabla de eventos sísmicos (para buscar sismos M4.5+)
TABLA_EVENTOS = "tbl_historico_sismico_raw"


def _znorm(c):
    m, s = np.nanmean(c), np.nanstd(c)
    if not np.isfinite(m) or not np.isfinite(s) or s < 1e-12:
        return np.full_like(c, np.nan)
    return (c - m) / s


def serie(conn_s, ts_fin: str):
    """{canal: (curva z-normalizada, media cruda)} de la ventana, o None."""
    ini = (dt.datetime.strptime(ts_fin[:16], "%Y-%m-%d %H:%M")
           - dt.timedelta(hours=VENTANA_H)).strftime("%Y-%m-%d %H:%M")
    cols = ", ".join(CANALES)
    filas = conn_s.execute(
        "SELECT timestamp_blk, " + cols + " FROM " + TABLA + " WHERE timestamp_blk >= ? AND timestamp_blk < ? "
        "ORDER BY timestamp_blk", (ini, ts_fin[:16])).fetchall()
    if len(filas) < N_BINS:
        return None
    t0 = dt.datetime.strptime(ini, "%Y-%m-%d %H:%M")
    ancho = VENTANA_H / N_BINS
    out = {}
    for j, canal in enumerate(CANALES, start=1):
        acc = [[] for _ in range(N_BINS)]
        for r in filas:
            v = r[j]
            if v is None:
                continue
            h = (dt.datetime.strptime(str(r[0])[:16], "%Y-%m-%d %H:%M")
                 - t0).total_seconds() / 3600.0
            i = int(h / ancho)
            if 0 <= i < N_BINS:
                acc[i].append(float(v))
        curva = np.array([(sum(a) / len(a)) if a else np.nan for a in acc])
        if np.sum(np.isfinite(curva)) < N_BINS // 2:
            continue
        out[canal] = (_znorm(curva), float(np.nanmean(curva)))
    return out or None


def parecido(a, b):
    rs = []
    for canal in set(a) & set(b):
        x, y = a[canal][0], b[canal][0]
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < N_BINS // 3:
            continue
        xv, yv = x[m], y[m]
        if np.std(xv) < 1e-12 or np.std(yv) < 1e-12:
            continue
        r = float(np.corrcoef(xv, yv)[0, 1])
        if np.isfinite(r):
            rs.append(r)
    return float(np.mean(rs)) if rs else None


def main():
    global VENTANA_H, SEP_H, SEMILLA, EPOCA_D, TABLA

    p = argparse.ArgumentParser(description="¿La telemetría de enjambres cambia antes de M4.5+?")
    p.add_argument("db", help="Ruta a la DB de eventos (se abre en mode=ro)")
    p.add_argument("db_enjambre", nargs="?", default=None, help="Ruta a la DB de enjambre (default: misma que db)")
    p.add_argument("--ventana-h", type=int, default=VENTANA_H)
    p.add_argument("--sep-h", type=int, default=SEP_H)
    p.add_argument("--semilla", type=int, default=SEMILLA)
    p.add_argument("--epoca-d", type=int, default=EPOCA_D)
    p.add_argument("--tabla", default=TABLA)
    p.add_argument("--output", default=None, help="Archivo donde guardar el resultado (además de stdout)")
    args = p.parse_args()
    VENTANA_H, SEP_H, SEMILLA, EPOCA_D = args.ventana_h, args.sep_h, args.semilla, args.epoca_d
    if SEP_H < VENTANA_H:
        SEP_H = VENTANA_H
    TABLA = args.tabla.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", TABLA):
        print(f"ERROR: nombre de tabla inválido: {TABLA!r}", file=sys.stderr)
        return 2
    db = args.db
    db_s = args.db_enjambre or db

    out_f = None
    if args.output:
        out_f = open(args.output, "w", encoding="utf-8")
        _stdout_orig = sys.stdout
        class _Tee:
            def write(self, s):
                _stdout_orig.write(s)
                out_f.write(s)
            def flush(self):
                _stdout_orig.flush()
                out_f.flush()
        sys.stdout = _Tee()

    print(f"ventana: {VENTANA_H} h · semilla de calma: {SEMILLA} · tabla: {TABLA}")
    print(f"epoca de empareje: ±{EPOCA_D} días · separacion minima: {SEP_H} h "
          f"({'sin solape' if SEP_H >= VENTANA_H else 'CON SOLAPE: las muestras no son independientes'})")
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
    cs = sqlite3.connect(f"file:{db_s}?mode=ro", uri=True, timeout=30)

    rango = c.execute("SELECT MIN(timestamp_blk), MAX(timestamp_blk), COUNT(*) FROM " + TABLA).fetchone()
    if not rango or not rango[0]:
        print("sin datos de enjambre: nada que medir")
        return 1
    print(f"Enjambre: {rango[2]:,} intervalos, {rango[0][:10]} -> {rango[1][:10]}")

    ev = c.execute(
        "SELECT timestamp_blk, id_nodo FROM tbl_historico_sismico_raw "
        "WHERE sismo_max_mag >= 4.5 AND timestamp_blk >= ? AND timestamp_blk <= ? "
        "ORDER BY timestamp_blk", (rango[0][:16], rango[1][:16])).fetchall()
    print(f"eventos M4.5+ dentro del periodo: {len(ev):,}")
    if not ev:
        print("sin eventos en el periodo con enjambre")
        return 1

    por_nodo = {}
    for ts, nd in ev:
        por_nodo.setdefault(int(nd), []).append(str(ts))
    horas = [r[0] for r in c.execute(
        "SELECT timestamp_blk FROM " + TABLA + " WHERE "
        "timestamp_blk >= ? AND timestamp_blk <= ? ORDER BY timestamp_blk",
        (rango[0][:16], rango[1][:16]))]
    reales = sorted(por_nodo)

    rng = random.Random(SEMILLA)

    def es_calma(ts_s, nodo, t):
        L = por_nodo.get(nodo)
        if not L:
            return True
        i = bisect.bisect_right(L, ts_s)
        return not (i < len(L) and L[i] <= (t + dt.timedelta(hours=HORIZONTE_H)
                                            ).strftime("%Y-%m-%d %H:%M"))

    usados, parejas = [], []
    paso = max(1, len(ev) // 600)
    for ts, nd in ev[::paso]:
        try:
            t = dt.datetime.strptime(str(ts)[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if any(abs((t - u).total_seconds()) / 3600.0 < SEP_H for u in usados):
            continue
        # Curva de la ventana del evento (serie() usa r[j]: cada canal lee su
        # propia columna; el bloque inline viejo leía r[1] en ambos canales).
        f_ev = serie(cs, str(ts)[:16])

        if f_ev is None:
            continue

        pareja = None
        for _ in range(500):
            tt = t + dt.timedelta(hours=rng.randint(-EPOCA_D, EPOCA_D) * 24)
            j = bisect.bisect_left(horas, tt.strftime("%Y-%m-%d %H:%M"))
            if j >= len(horas):
                continue
            ts2, nodo2 = str(horas[j]), reales[rng.randrange(len(reales))]
            t2 = dt.datetime.strptime(ts2[:16], "%Y-%m-%d %H:%M")
            if nodo2 == int(nd) or abs((t2 - t).total_seconds()) / 3600.0 < SEP_H:
                continue
            if any(abs((t2 - u).total_seconds()) / 3600.0 < SEP_H for u in usados):
                continue
            if not es_calma(ts2, nodo2, t2):
                continue
            # Curva de la ventana de calma (serie() con r[j], como arriba).
            t2_str = t2.strftime("%Y-%m-%d %H:%M")
            f_ca = serie(cs, t2_str)
            if f_ca:
                pareja = (t2, f_ca)
                break

        if pareja is None:
            continue

        parejas.append((t, f_ev, pareja[0], pareja[1]))
        usados += [t, pareja[0]]

    if len(parejas) < 10:
        print(f"\nsolo {len(parejas)} parejas con enjambre en ambas ventanas: "
              f"muestra insuficiente para concluir. No se inventa un veredicto.")
        if out_f is not None:
            sys.stdout.flush()
            sys.stdout = sys.__stdout__
            out_f.close()
        return 1

    te = [p[0] for p in parejas]
    print(f"\nparejas emparejadas por epoca: {len(parejas)} "
          f"({min(te).date()} -> {max(te).date()})")
    print(f"canales con curva: {sorted(parejas[0][1])}")

    # ── 1. NIVEL ────────────────────────────────────────────────────────────
    print("\n=== 1. NIVEL: la media de la ventana difiere? ===")
    print(f"  {'canal':10} {'evento':>12} {'calma':>12} {'dif':>10} {'dif/sd':>8}")
    for canal in CANALES:
        a = [p[1][canal][1] for p in parejas if canal in p[1]]
        b = [p[3][canal][1] for p in parejas if canal in p[3]]
        if len(a) < 10 or len(b) < 10:
            print(f"  {canal:10} muestra insuficiente ({len(a)}/{len(b)})")
            continue
        d = st.mean(a) - st.mean(b)
        sd = st.pstdev(a + b) or 1e-12
        print(f"  {canal:10} {st.mean(a):12.4f} {st.mean(b):12.4f} "
              f"{d:+10.4f} {d / sd:+8.3f}")
    print("  (dif/sd es el tamano del efecto: |0,2| chico, |0,5| medio)")

    # ── 2. FORMA ────────────────────────────────────────────────────────────
    EV = [p[1] for p in parejas]
    CA = [p[3] for p in parejas]

    def pares(A, B, mismo=False):
        o = []
        for i, fa in enumerate(A):
            for j, fb in enumerate(B):
                if mismo and j <= i:
                    continue
                p = parecido(fa, fb)
                if p is not None:
                    o.append(p)
        return o

    ee, ec, cc = pares(EV, EV, True), pares(EV, CA), pares(CA, CA, True)
    print("\n=== 2. FORMA: la curva se repite entre eventos? ===")
    for v, et in ((ee, "EVENTO vs EVENTO"), (ec, "evento vs CALMA (nulo)"),
                  (cc, "calma  vs calma")):
        if not v:
            print(f"  {et}: sin pares")
            continue
        s = sorted(v)
        print(f"  {et:26} n={len(v):6} media={st.mean(v):+.4f} "
              f"mediana={s[len(s) // 2]:+.4f} p99={s[int(.99 * (len(s) - 1))]:+.4f}")
    if ee and ec:
        print(f"\n  ev-ev menos ev-calma: {st.mean(ee) - st.mean(ec):+.4f}")
        print(f"  {'umbral':>7} {'ev-ev':>9} {'ev-calma':>9} {'lift':>8}")
        for u in (0.3, 0.5, 0.7):
            pe = sum(1 for x in ee if x >= u) / len(ee)
            pc = sum(1 for x in ec if x >= u) / len(ec)
            print(f"  {u:7.2f} {pe:9.4f} {pc:9.4f} "
                  f"{(pe + 1e-4) / (pc + 1e-4):7.2f}x")

    if out_f is not None:
        sys.stdout.flush()
        sys.stdout = sys.__stdout__
        out_f.close()
        print(f"[output guardado en {args.output}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())