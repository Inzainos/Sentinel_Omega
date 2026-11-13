"""¿La MIGRACIÓN DE ENJAMBRES (Omori difuso) precede a mainshocks M≥5.5?
Modelo nulo: misma ubicación, ventana de calma sin mainshock en horizonte.

Por qué podría funcionar:
- Omori difuso: sismicidad menor migra hacia la zona de ruptura antes del mainshock
- Datos en tbl_eventos_sismicos_fuente (220k hipocentros 1994-2026 con lat/lon/prof/mag)
- Comparación contra ventanas de CALMA en MISMA ubicación, emparejadas por época

Uso: .venv/bin/python deploy/medir_enjambre_migracion.py <db> [VENTANA_H [RADIO_KM [MAG_MIN [SEP_H [SEMILLA [EPOCA_D]]]]]]
"""

from __future__ import annotations

import argparse
import bisect
import datetime as dt
import random
import sqlite3
import statistics as st
import sys

import numpy as np

# NOTA tuning P3 2026-11-10: sys.path hardcodeado eliminado (no se importa nada
# de sentinel_omega). Args con argparse (antes: sys.argv[1] sin comprobar ->
# IndexError) + --output a archivo (antes: solo stdout). Timestamps parseados
# UNA vez (antes: strptime por evento en cada llamada a curva_migracion);
# hay_mainshock_en_horizonte y el chequeo de usados usan bisect sobre listas
# ordenadas (antes: escaneo lineal por nodo / por lista de usados).

# Parámetros por defecto
VENTANA_H = 336          # 14 días antes del mainshock
RADIO_KM = 100           # Radio alrededor del mainshock para buscar pre-sismicidad
MAG_MIN = 2.5            # Magnitud mínima de eventos a considerar
SEP_H = 336              # Separación mínima entre ventanas (sin solape)
SEMILLA = 53
EPOCA_D = 180            # ±180 días para emparejar calma
HORIZONTE_H = 190        # Horizonte de predicción (calma = sin M≥5.5 en este horizonte)
N_BINS_TEMP = 24         # Bines temporales para curva de migración

TABLA_EVENTOS = "tbl_eventos_sismicos_fuente"


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos puntos (fórmula haversine, vectorizada)."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _znorm(c):
    m, s = np.nanmean(c), np.nanstd(c)
    if not np.isfinite(m) or not np.isfinite(s) or s < 1e-12:
        return np.full_like(c, np.nan)
    return (c - m) / s


def curva_migracion(eventos, t_main, lat_main, lon_main):
    """
    Calcula curva de migración: distancia media normalizada vs tiempo antes del mainshock.
    Retorna (curva_z, pendiente_raw, dist_media) o None si insuficientes datos.
    `eventos` es una lista de (t_datetime, lat, lon, mag) con timestamps YA
    parseados una sola vez por el llamador (nunca strptime aquí).
    """
    if not eventos:
        return None
    # Vectorizar: horas antes + distancia en arrays NumPy
    t_ev = np.array([e[0] for e in eventos], dtype='datetime64[s]')
    t_m = np.datetime64(t_main)
    h_antes = (t_m - t_ev).astype('timedelta64[s]').astype(float) / 3600.0
    mask = (h_antes > 0) & (h_antes <= VENTANA_H)
    if not np.any(mask):
        return None
    lat = np.array([e[1] for e in eventos], dtype=float)
    lon = np.array([e[2] for e in eventos], dtype=float)
    d = haversine_km(lat[mask], lon[mask], lat_main, lon_main)
    ok = d <= RADIO_KM
    if int(ok.sum()) < 10:  # Mínimo eventos para curva significativa
        return None
    h_sel = h_antes[mask][ok]
    d_sel = d[ok]

    # Bines temporales (bin 0 = más cerca del mainshock = últimas horas)
    ancho_t = VENTANA_H / N_BINS_TEMP
    bin_idx = ((VENTANA_H - h_sel) / ancho_t).astype(int)
    bin_idx = np.clip(bin_idx, 0, N_BINS_TEMP - 1)
    d_norm = d_sel / RADIO_KM  # Distancia normalizada 0-1

    # Curva: distancia media normalizada por bin temporal
    curva = np.full(N_BINS_TEMP, np.nan)
    for i in range(N_BINS_TEMP):
        m = bin_idx == i
        if np.any(m):
            curva[i] = np.mean(d_norm[m])

    if np.sum(np.isfinite(curva)) < N_BINS_TEMP // 2:
        return None

    curva_znorm = _znorm(curva)

    # Pendiente: si migra HACIA el mainshock, distancia disminuye -> pendiente negativa
    x = np.arange(N_BINS_TEMP)
    m = np.isfinite(curva)
    if m.sum() < 3:
        return None
    slope = float(np.polyfit(x[m], curva[m], 1)[0])

    dist_media = float(np.nanmean(curva))

    return (curva_znorm, slope, dist_media)


def main():
    global VENTANA_H, RADIO_KM, MAG_MIN, SEP_H, SEMILLA, EPOCA_D

    p = argparse.ArgumentParser(description="¿Migración de enjambres precede a mainshocks M>=5.5?")
    p.add_argument("db", help="Ruta a la DB SQLite (se abre en mode=ro)")
    p.add_argument("--ventana-h", type=int, default=VENTANA_H)
    p.add_argument("--radio-km", type=int, default=RADIO_KM)
    p.add_argument("--mag-min", type=float, default=MAG_MIN)
    p.add_argument("--sep-h", type=int, default=SEP_H)
    p.add_argument("--semilla", type=int, default=SEMILLA)
    p.add_argument("--epoca-d", type=int, default=EPOCA_D)
    p.add_argument("--output", default=None, help="Archivo donde guardar el resultado (además de stdout)")
    args = p.parse_args()
    VENTANA_H, RADIO_KM, MAG_MIN = args.ventana_h, args.radio_km, args.mag_min
    SEP_H, SEMILLA, EPOCA_D = args.sep_h, args.semilla, args.epoca_d
    if SEP_H < VENTANA_H:
        SEP_H = VENTANA_H
    db = args.db

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

    print(f"ventana: {VENTANA_H} h · radio: {RADIO_KM} km · mag_min: {MAG_MIN}")
    print(f"semilla: {SEMILLA} · época empareje: ±{EPOCA_D} d · sep: {SEP_H} h "
          f"({'sin solape' if SEP_H >= VENTANA_H else 'CON SOLAPE'})")

    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)

    # Cargar TODOS los eventos M≥MAG_MIN
    print("Cargando catálogo completo...")
    all_ev = c.execute(
        f"SELECT time_utc, lat, lon, mag, depth_km, id_nodo FROM {TABLA_EVENTOS} "
        f"WHERE mag >= ? ORDER BY time_utc", (MAG_MIN,)).fetchall()
    print(f"Eventos totales M≥{MAG_MIN}: {len(all_ev):,}")

    if not all_ev:
        print("Catálogo vacío")
        return 1

    # Timestamps parseados UNA vez (datetime64): antes se hacía strptime por
    # evento en cada llamada a curva_migracion (miles de veces por mainshock).
    times_all = np.array([r[0][:19] for r in all_ev], dtype='datetime64[s]')
    ev_parsed = [(t, r[1], r[2], r[3]) for t, r in zip(
        [dt.datetime.strptime(r[0][:19], "%Y-%m-%d %H:%M:%S") for r in all_ev], all_ev)]

    # Mainshocks M≥5.5
    mainshocks = [(t, r[1], r[2], r[3], r[4], r[5])
                  for t, r in zip(
                      [dt.datetime.strptime(r[0][:19], "%Y-%m-%d %H:%M:%S") for r in all_ev], all_ev)
                  if r[3] >= 5.5]
    print(f"Mainshocks M≥5.5: {len(mainshocks):,}")

    if len(mainshocks) < 20:
        print("Pocos mainshocks para análisis estadístico")
        return 1

    # Mainshocks por nodo con tiempos ordenados (para bisect en horizonte)
    main_by_nodo = {}
    for ms in mainshocks:
        main_by_nodo.setdefault(ms[5], []).append(ms[0])
    for nodo in main_by_nodo:
        main_by_nodo[nodo].sort()

    def hay_mainshock_en_horizonte(t_inicio, nodo, horizonte_h):
        """Verifica si hay M≥5.5 en [t_inicio, t_inicio + horizonte_h] para este nodo (bisect)."""
        tiempos = main_by_nodo.get(nodo)
        if not tiempos:
            return False
        t_fin = t_inicio + dt.timedelta(hours=horizonte_h)
        i = bisect.bisect_left(tiempos, t_inicio)
        return i < len(tiempos) and tiempos[i] <= t_fin

    def eventos_en_ventana(t_fin, ventana_h):
        """Retorna eventos (t_datetime, lat, lon, mag) en [t_fin - ventana_h, t_fin] (bisect)."""
        t_ini = t_fin - dt.timedelta(hours=ventana_h)
        i0 = bisect.bisect_left(times_all, np.datetime64(t_ini))
        i1 = bisect.bisect_right(times_all, np.datetime64(t_fin))
        return ev_parsed[i0:i1]

    # Ventanas ya usadas, ORDENADAS: el choque con SEP_H solo puede venir de
    # vecinos inmediatos (bisect), no de escanear toda la lista por candidato.
    usados = []

    def choca_usados(t):
        i = bisect.bisect_left(usados, t)
        for j in (i - 1, i):
            if 0 <= j < len(usados):
                if abs((t - usados[j]).total_seconds()) / 3600.0 < SEP_H:
                    return True
        return False

    rng = random.Random(SEMILLA)

    parejas = []
    paso = max(1, len(mainshocks) // 800)  # Muestrear ~800 mainshocks

    for t_main, lat_m, lon_m, mag_m, prof_m, nodo_m in mainshocks[::paso]:
        if choca_usados(t_main):
            continue

        # Eventos en ventana del mainshock (MISMA ubicación)
        ev_ventana = eventos_en_ventana(t_main, VENTANA_H)
        curva_ev = curva_migracion(ev_ventana, t_main, lat_m, lon_m)
        if curva_ev is None:
            continue

        # Buscar ventana de CALMA emparejada: MISMA ubicación, época distinta
        pareja = None
        for _ in range(2000):
            delta_dias = rng.randint(-EPOCA_D, EPOCA_D)
            t_calma = t_main + dt.timedelta(days=delta_dias)

            if choca_usados(t_calma):
                continue

            # Verificar que es calma: no hay M≥5.5 en horizonte EN ESTE NODO
            if hay_mainshock_en_horizonte(t_calma, nodo_m, HORIZONTE_H):
                continue

            # MISMA ubicación (lat_m, lon_m), época distinta
            ev_calma = eventos_en_ventana(t_calma, VENTANA_H)
            curva_ca = curva_migracion(ev_calma, t_calma, lat_m, lon_m)
            if curva_ca is None:
                continue

            pareja = (t_calma, curva_ca)
            break

        if pareja is None:
            continue

        parejas.append((t_main, curva_ev, pareja[0], pareja[1]))
        bisect.insort(usados, t_main)
        bisect.insort(usados, pareja[0])
        if len(parejas) % 100 == 0:
            print(f"  ... {len(parejas)} parejas")

    if len(parejas) < 15:
        print(f"\nSolo {len(parejas)} parejas: muestra insuficiente. No se inventa veredicto.")
        if out_f is not None:
            sys.stdout.flush()
            sys.stdout = sys.__stdout__
            out_f.close()
        return 1

    te = [p[0] for p in parejas]
    print(f"\nParejas emparejadas por época: {len(parejas)} ({min(te).date()} -> {max(te).date()})")
    print(f"Mainshocks M≥5.5 únicos: {len(set(p[0] for p in parejas))}")

    # ── 1. PENDIENTE DE MIGRACIÓN ───────────────────────────────────────────
    print("\n=== 1. PENDIENTE MIGRACIÓN (distancia normalizada vs tiempo) ===")
    print(f"  {'tipo':12} {'pendiente':>10} {'media_dist':>10} {'n':>6}")
    slopes_ev = [p[1][1] for p in parejas]
    slopes_ca = [p[3][1] for p in parejas]
    dist_ev = [p[1][2] for p in parejas]
    dist_ca = [p[3][2] for p in parejas]

    print(f"  {'evento':12} {st.mean(slopes_ev):+10.5f} {st.mean(dist_ev):10.4f} {len(slopes_ev):6}")
    print(f"  {'calma':12} {st.mean(slopes_ca):+10.5f} {st.mean(dist_ca):10.4f} {len(slopes_ca):6}")
    d_slope = st.mean(slopes_ev) - st.mean(slopes_ca)
    sd_slope = st.pstdev(slopes_ev + slopes_ca) or 1e-12
    print(f"  {'dif (ev-ca)':12} {d_slope:+10.5f} {'':10} {d_slope/sd_slope:+8.3f}σ")
    print("  (pendiente NEGATIVA = migración HACIA epicentro; evento más negativo que calma = precursora)")

    # ── 2. FORMA DE LA CURVA (correlación cruzada) ──────────────────────────
    EV_curvas = [p[1][0] for p in parejas]
    CA_curvas = [p[3][0] for p in parejas]

    def pares_corr(A, B, mismo=False):
        o = []
        for i, a in enumerate(A):
            for j, b in enumerate(B):
                if mismo and j <= i:
                    continue
                m = np.isfinite(a) & np.isfinite(b)
                if m.sum() < N_BINS_TEMP // 3:
                    continue
                r = float(np.corrcoef(a[m], b[m])[0, 1])
                if np.isfinite(r):
                    o.append(r)
        return o

    ee = pares_corr(EV_curvas, EV_curvas, True)
    ec = pares_corr(EV_curvas, CA_curvas)
    cc = pares_corr(CA_curvas, CA_curvas, True)

    print("\n=== 2. FORMA: correlación de curvas de migración ===")
    for v, et in ((ee, "EVENTO vs EVENTO"), (ec, "evento vs CALMA (nulo)"), (cc, "calma vs calma")):
        if not v:
            print(f"  {et}: sin pares")
            continue
        s = sorted(v)
        print(f"  {et:26} n={len(v):6} media={st.mean(v):+.4f} mediana={s[len(s)//2]:+.4f} p99={s[int(.99*(len(s)-1))]:+.4f}")

    if ee and ec:
        lift = (st.mean(ee) + 1e-4) / (st.mean(ec) + 1e-4)
        print(f"\n  ev-ev menos ev-calma: {st.mean(ee) - st.mean(ec):+.4f}")
        print(f"  Lift medio (ee/ec): {lift:.2f}x")

    # ── 3. UMBRAL: % eventos con pendiente más negativa que calma ───────────
    if slopes_ev and slopes_ca:
        print("\n=== 3. CLASIFICACIÓN: pendiente más negativa que nulo ===")
        for u in (-0.05, -0.1, -0.15, -0.2):
            pe = sum(1 for x in slopes_ev if x <= u) / len(slopes_ev)
            pc = sum(1 for x in slopes_ca if x <= u) / len(slopes_ca)
            lift = (pe + 1e-4) / (pc + 1e-4)
            print(f"  slope ≤ {u:+.2f}: evento={pe:.3f} calma={pc:.3f} lift={lift:.2f}x")

    if out_f is not None:
        sys.stdout.flush()
        sys.stdout = sys.__stdout__
        out_f.close()
        print(f"[output guardado en {args.output}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())