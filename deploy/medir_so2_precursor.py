"""¿La DESGASIFICACIÓN VOLCÁNICA (SO₂, proxy radón) precede a sismos M≥5.5 cercanos?

Hipótesis: Aumento anómalo de SO₂ en volcán precede a sismo M≥5.5 en radio R km en ventana de H horas.
Modelo nulo: Misma ventana espacial, épocas aleatorias sin sismo M≥5.5 posterior.

Uso: .venv/bin/python deploy/medir_so2_precursor.py <db> [VENTANA_H [RADIO_KM [MAG_MIN [SEP_H [SEMILLA [EPOCA_D]]]]]]
"""

from __future__ import annotations

import argparse
import bisect
import datetime as dt
import math
import random
import sqlite3
import statistics as st
import sys

import numpy as np

# NOTA tuning P3 2026-11-10: sys.path hardcodeado eliminado (no se importa nada
# de sentinel_omega). Args con argparse (antes: sys.argv[1] sin comprobar ->
# IndexError) + --output a archivo (antes: solo stdout). Código muerto
# borrado: bucle volc_coords con `pass` (nunca se poblaba ni usaba), dict
# `vlat` (construido y sin uso), parámetros lat_volc/lon_volc de curva_so2
# (sin uso). Timestamps SO₂ parseados UNA vez (datetime64) + bisect en
# so2_en_ventana y hay_sismo_en_horizonte (antes: strptime por registro en
# cada llamada y escaneo lineal). Volcanes añadidos al mapa (antes excluidos
# pese a tener datos): Eyjafjallajokull (37 filas; 63.620, -19.613, Wikipedia)
# y Popocatepetl (6 filas; 19.02222, -98.62778, Wikipedia).
# DATO (verificado vivo 2026-11-10): 2,956 filas SO₂ en 157 volcanes
# (1978-12-05 -> 2026-08-31); el mapa cubre 22. La densidad sigue siendo
# ~3 filas/volcán/año: curva_so2 exige >=5 registros en 720 h y >=12 bins
# finitos de 24, casi imposible. Sin fuente de cadencia real (p. ej. TROPOMI
# diario) el estudio no puede medir; la decisión (fuente o archivar) queda
# para Elán/coordinador.

# Parámetros por defecto
VENTANA_H = 720          # 30 días antes del sismo
RADIO_KM = 200           # Radio alrededor del volcán para buscar sismos
MAG_MIN = 5.5            # Magnitud mínima del sismo objetivo
SEP_H = 720              # Separación mínima entre ventanas
SEMILLA = 53
EPOCA_D = 180            # ±180 días para emparejar calma
HORIZONTE_H = 190        # Horizonte: calma = sin M≥5.5 en este horizonte
N_BINS = 24              # Bines temporales para curva SO₂

TABLA_SO2 = "tbl_desgasificacion_raw"
TABLA_SISMOS = "tbl_eventos_sismicos_fuente"


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _znorm(c):
    m, s = np.nanmean(c), np.nanstd(c)
    if not np.isfinite(m) or not np.isfinite(s) or s < 1e-12:
        return np.full_like(c, np.nan)
    return (c - m) / s


def curva_so2(registros, t_evento):
    """
    Calcula curva de SO₂ normalizada en ventana antes del evento.
    Retorna (curva_z, slope, media) o None.
    `registros` es una lista de (t_datetime, so2_kt) con timestamps YA
    parseados una sola vez por el llamador.
    """
    pre = []
    for t_so2, so2 in registros:
        if t_so2 >= t_evento:
            continue
        h_antes = (t_evento - t_so2).total_seconds() / 3600.0
        if h_antes > VENTANA_H:
            continue
        pre.append((h_antes, so2))  # (horas_antes, so2_kt)

    if len(pre) < 5:
        return None

    pre.sort(key=lambda x: x[0])

    ancho_t = VENTANA_H / N_BINS
    bins = [[] for _ in range(N_BINS)]
    for h, so2 in pre:
        i = int((VENTANA_H - h) / ancho_t)
        if 0 <= i < N_BINS:
            bins[i].append(so2)

    curva = []
    for i in range(N_BINS):
        if bins[i]:
            curva.append(np.mean(bins[i]))
        else:
            curva.append(np.nan)

    if np.sum(np.isfinite(curva)) < N_BINS // 2:
        return None

    curva_arr = np.array(curva)
    curva_znorm = _znorm(curva_arr)

    # Pendiente: SO₂ creciendo antes del sismo = pendiente POSITIVA
    x = np.arange(N_BINS)
    m = np.isfinite(curva_arr)
    if m.sum() < 3:
        return None
    slope = float(np.polyfit(x[m], curva_arr[m], 1)[0])

    media = float(np.nanmean(curva_arr))
    return (curva_znorm, slope, media)


def main():
    global VENTANA_H, RADIO_KM, MAG_MIN, SEP_H, SEMILLA, EPOCA_D

    p = argparse.ArgumentParser(description="¿SO2 volcánico precede a sismos M>=MAG_MIN cercanos?")
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

    print(f"ventana: {VENTANA_H} h · radio volcán-sismo: {RADIO_KM} km · mag_min: {MAG_MIN}")
    print(f"semilla: {SEMILLA} · época empareje: ±{EPOCA_D} d · sep: {SEP_H} h "
          f"({'sin solape' if SEP_H >= VENTANA_H else 'CON SOLAPE'})")

    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)

    # Cargar datos SO₂ con coordenadas de volcanes (necesito lat/lon de volcanes)
    # La tabla solo tiene nombre de volcán. Necesito coordenadas.
    # Voy a usar una tabla de coordenadas de volcanes conocidos o buscar en sismos cercanos.
    print("Cargando datos SO₂...")
    so2_raw = c.execute(
        f"SELECT timestamp_blk, volcan, so2_kt FROM {TABLA_SO2} "
        f"WHERE so2_kt > 0 ORDER BY timestamp_blk").fetchall()
    print(f"Registros SO₂ > 0: {len(so2_raw):,}")

    if not so2_raw:
        print("Sin datos SO₂")
        return 1

    # Coordenadas conocidas de volcanes principales (lat, lon). Las dos
    # últimas se añadieron en tuning P3 (antes excluidas pese a tener datos):
    # Eyjafjallajokull 63.620, -19.613 y Popocatepetl 19.02222, -98.62778
    # (Wikipedia, verificadas 2026-11-10). Claves sin diacríticos, como en la tabla.
    VOLCAN_COORDS = {
        "Nyamuragira": (-1.408, 29.200),
        "Kliuchevskoi": (56.056, 160.642),
        "Kilauea": (19.419, -155.288),
        "Piton_de_la_Fournaise": (-21.244, 55.708),
        "Etna": (37.748, 14.999),
        "Sierra_Negra": (-0.833, -91.167),
        "La_Palma": (28.573, -17.839),
        "Nishinoshima": (27.247, 140.874),
        "Bromo": (-7.942, 112.950),
        "Home_Reef": (-18.992, -174.775),
        "Wolf": (0.020, -91.350),
        "Cerro_Azul": (-0.920, -91.408),
        "Raung": (-8.119, 114.056),
        "Ambae": (-15.389, 167.835),
        "Nabro": (13.370, 41.700),
        "Lewotobi": (-8.542, 122.770),
        "Fagradalsfjall": (63.891, -22.258),
        "Holuhraun": (64.733, -16.617),
        "Zhupanovsky": (53.589, 159.150),
        "Anatahan": (16.350, 145.670),
        "Eyjafjallajokull": (63.620, -19.613),
        "Popocatepetl": (19.02222, -98.62778),
    }

    # Agrupar SO₂ por volcán, con timestamps parseados UNA vez
    so2_by_volc = {}
    so2_times = {}
    for ts, volc, so2 in so2_raw:
        if volc in VOLCAN_COORDS:
            so2_by_volc.setdefault(volc, []).append(
                (dt.datetime.strptime(ts[:16], "%Y-%m-%d %H:%M"), so2))
    for volc, regs in so2_by_volc.items():
        so2_times[volc] = np.array([r[0] for r in regs], dtype='datetime64[s]')

    print(f"Volcanes con coordenadas y datos SO₂: {len(so2_by_volc)}")

    # Cargar sismos M≥MAG_MIN
    print("Cargando sismos...")
    sismos = c.execute(
        f"SELECT time_utc, lat, lon, mag, depth_km FROM {TABLA_SISMOS} "
        f"WHERE mag >= ? ORDER BY time_utc", (MAG_MIN,)).fetchall()
    print(f"Sismos M≥{MAG_MIN}: {len(sismos):,}")

    if not sismos:
        print("Sin sismos objetivo")
        return 1

    # Para cada sismo, encontrar volcán más cercano con datos SO₂
    sismos_con_volc = []
    for ts, lat, lon, mag, dep in sismos:
        t_sismo = dt.datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
        best_volc = None
        best_dist = float('inf')
        for volc, (vlat, vlon) in VOLCAN_COORDS.items():
            if volc not in so2_by_volc:
                continue
            d = haversine_km(lat, lon, vlat, vlon)
            if d < best_dist and d <= RADIO_KM:
                best_dist = d
                best_volc = volc
        if best_volc:
            sismos_con_volc.append((t_sismo, lat, lon, mag, dep, best_volc, best_dist))

    print(f"Sismos con volcán cercano (≤{RADIO_KM} km) y datos SO₂: {len(sismos_con_volc):,}")

    if len(sismos_con_volc) < 20:
        print("Pocos sismos emparejados con volcanes")
        return 1

    # Agrupar por volcán para verificación de horizonte (tiempos ordenados)
    sismos_by_volc = {}
    for s in sismos_con_volc:
        sismos_by_volc.setdefault(s[5], []).append(s[0])
    for volc in sismos_by_volc:
        sismos_by_volc[volc].sort()

    rng = random.Random(SEMILLA)

    def hay_sismo_en_horizonte(t_inicio, volc, horizonte_h):
        """¿Hay M≥MAG_MIN en [t_inicio, t_inicio+horizonte_h] para este volcán? (bisect)."""
        tiempos = sismos_by_volc.get(volc)
        if not tiempos:
            return False
        t_fin = t_inicio + dt.timedelta(hours=horizonte_h)
        i = bisect.bisect_left(tiempos, t_inicio)
        return i < len(tiempos) and tiempos[i] <= t_fin

    def so2_en_ventana(volc, t_fin, ventana_h):
        """Registros SO₂ (t_datetime, so2) de `volc` en [t_fin-ventana_h, t_fin) (bisect)."""
        regs = so2_by_volc.get(volc)
        if not regs:
            return []
        times = so2_times[volc]
        i0 = int(np.searchsorted(times, np.datetime64(t_fin - dt.timedelta(hours=ventana_h))))
        i1 = int(np.searchsorted(times, np.datetime64(t_fin)))
        return regs[i0:i1]

    usados = []
    parejas = []
    paso = max(1, len(sismos_con_volc) // 500)

    for t_sismo, lat, lon, mag, dep, volc, dist in sismos_con_volc[::paso]:
        if any(abs((t_sismo - u).total_seconds()) / 3600.0 < SEP_H for u in usados):
            continue

        # SO₂ en ventana del sismo
        so2_ev = so2_en_ventana(volc, t_sismo, VENTANA_H)
        curva_ev = curva_so2(so2_ev, t_sismo)
        if curva_ev is None:
            continue

        # Buscar ventana de CALMA: MISMO volcán, época distinta
        pareja = None
        for _ in range(2000):
            delta_dias = rng.randint(-EPOCA_D, EPOCA_D)
            t_calma = t_sismo + dt.timedelta(days=delta_dias)

            if any(abs((t_calma - u).total_seconds()) / 3600.0 < SEP_H for u in usados):
                continue

            if hay_sismo_en_horizonte(t_calma, volc, HORIZONTE_H):
                continue

            so2_ca = so2_en_ventana(volc, t_calma, VENTANA_H)
            curva_ca = curva_so2(so2_ca, t_calma)
            if curva_ca is None:
                continue

            pareja = (t_calma, curva_ca)
            break

        if pareja is None:
            continue

        parejas.append((t_sismo, curva_ev, pareja[0], pareja[1]))
        usados += [t_sismo, pareja[0]]
        if len(parejas) % 50 == 0:
            print(f"  ... {len(parejas)} parejas")

    if len(parejas) < 15:
        print(f"\nSolo {len(parejas)} parejas: muestra insuficiente.")
        if out_f is not None:
            sys.stdout.flush()
            sys.stdout = sys.__stdout__
            out_f.close()
        return 1

    te = [p[0] for p in parejas]
    print(f"\nParejas emparejadas: {len(parejas)} ({min(te).date()} -> {max(te).date()})")

    # ── 1. NIVEL SO₂ ────────────────────────────────────────────────────────
    print("\n=== 1. NIVEL SO₂: media de ventana difiere? ===")
    print(f"  {'tipo':10} {'media_so2':>10} {'slope':>10} {'n':>6}")
    slopes_ev = [p[1][1] for p in parejas]
    slopes_ca = [p[3][1] for p in parejas]
    media_ev = [p[1][2] for p in parejas]
    media_ca = [p[3][2] for p in parejas]

    print(f"  {'evento':10} {st.mean(media_ev):10.2f} {st.mean(slopes_ev):+10.5f} {len(slopes_ev):6}")
    print(f"  {'calma':10} {st.mean(media_ca):10.2f} {st.mean(slopes_ca):+10.5f} {len(slopes_ca):6}")
    d_slope = st.mean(slopes_ev) - st.mean(slopes_ca)
    sd_slope = st.pstdev(slopes_ev + slopes_ca) or 1e-12
    print(f"  {'dif slope':10} {'':10} {d_slope:+10.5f} {d_slope/sd_slope:+8.3f}σ")
    print("  (slope POSITIVO = SO₂ creciendo; evento > calma = precursora)")

    # ── 2. FORMA ────────────────────────────────────────────────────────────
    EV_curvas = [p[1][0] for p in parejas]
    CA_curvas = [p[3][0] for p in parejas]

    def pares_corr(A, B, mismo=False):
        o = []
        for i, a in enumerate(A):
            for j, b in enumerate(B):
                if mismo and j <= i:
                    continue
                m = np.isfinite(a) & np.isfinite(b)
                if m.sum() < N_BINS // 3:
                    continue
                r = float(np.corrcoef(a[m], b[m])[0, 1])
                if np.isfinite(r):
                    o.append(r)
        return o

    ee = pares_corr(EV_curvas, EV_curvas, True)
    ec = pares_corr(EV_curvas, CA_curvas)
    cc = pares_corr(CA_curvas, CA_curvas, True)

    print("\n=== 2. FORMA: correlación de curvas SO₂ ===")
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

    # ── 3. CLASIFICACIÓN ────────────────────────────────────────────────────
    print("\n=== 3. CLASIFICACIÓN: slope más positivo que nulo ===")
    for u in (0.01, 0.05, 0.1, 0.2):
        pe = sum(1 for x in slopes_ev if x >= u) / len(slopes_ev)
        pc = sum(1 for x in slopes_ca if x >= u) / len(slopes_ca)
        lift = (pe + 1e-4) / (pc + 1e-4)
        print(f"  slope ≥ {u:.2f}: evento={pe:.3f} calma={pc:.3f} lift={lift:.2f}x")

    if out_f is not None:
        sys.stdout.flush()
        sys.stdout = sys.__stdout__
        out_f.close()
        print(f"[output guardado en {args.output}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())