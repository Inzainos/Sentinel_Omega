"""¿CLIMA ESPACIAL precede a M≥5.5? Versión ultra-rápida con arrays NumPy."""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import random
import sqlite3
import statistics as st
import sys

import numpy as np

# NOTA tuning P3 2026-11-10: sys.path hardcodeado eliminado (este script no importa
# nada de sentinel_omega; solo stdlib + numpy). Args validados con argparse
# (antes: sys.argv[1] sin comprobar -> IndexError) y --output a archivo
# (antes: solo stdout, el resultado se evaporaba).

VENTANA_H = 168
MAG_MIN = 5.5
SEMILLA = 53
QUINCENA_D = 15
N_BINS = 24

TABLA_CLIMA = "tbl_clima_espacial_raw"
TABLA_SISMOS = "tbl_eventos_sismicos_fuente"


def slope_from_times_values(times, values, t_evento, ventana_h, n_bins):
    """Pendiente y media usando arrays NumPy (vectorizado)."""
    # Máscara vectorizada
    h_antes = (t_evento - times).astype('timedelta64[h]').astype(float)
    mask = (h_antes > 0) & (h_antes <= ventana_h)
    if not np.any(mask):
        return None
    h_sel = h_antes[mask]
    v_sel = values[mask]
    if len(v_sel) < n_bins // 2:
        return None

    # Bineo vectorizado
    bin_idx = ((ventana_h - h_sel) / (ventana_h / n_bins)).astype(int)
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)

    # Media por bin
    curva = np.full(n_bins, np.nan)
    for i in range(n_bins):
        m = bin_idx == i
        if np.any(m):
            curva[i] = np.mean(v_sel[m])

    if np.sum(np.isfinite(curva)) < 3:
        return None

    x = np.arange(n_bins)
    m = np.isfinite(curva)
    slope = float(np.polyfit(x[m], curva[m], 1)[0])
    media = float(np.nanmean(curva))
    return (slope, media)


def main():
    global VENTANA_H, MAG_MIN, SEMILLA

    p = argparse.ArgumentParser(description="¿Clima espacial precede a M>=MAG_MIN?")
    p.add_argument("db", help="Ruta a la DB SQLite (se abre en mode=ro)")
    p.add_argument("--ventana-h", type=int, default=VENTANA_H)
    p.add_argument("--mag-min", type=float, default=MAG_MIN)
    p.add_argument("--semilla", type=int, default=SEMILLA)
    p.add_argument("--output", default=None, help="Archivo donde guardar el resultado (además de stdout)")
    args = p.parse_args()
    VENTANA_H, MAG_MIN, SEMILLA = args.ventana_h, args.mag_min, args.semilla
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

    print(f"ventana: {VENTANA_H}h mag:{MAG_MIN} semilla:{SEMILLA} control:±{QUINCENA_D}d")

    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)

    # Cargar clima como arrays NumPy (una sola vez)
    print("Cargando clima...")
    clima = c.execute(
        f"SELECT timestamp_blk, kp_promedio, kp_max, bz_promedio, bz_min, "
        f"viento_solar_avg, viento_solar_max, proton_flux_10mev, densidad_protones "
        f"FROM {TABLA_CLIMA} ORDER BY timestamp_blk").fetchall()

    # Convertir a arrays
    times_clima = np.array([dt.datetime.strptime(r[0][:16], "%Y-%m-%d %H:%M") for r in clima], dtype='datetime64[s]')
    años_clima = np.array([t.astype('datetime64[Y]').astype(int) + 1970 for t in times_clima])

    vars_clima = {
        "kp_prom": np.array([r[1] if r[1] is not None else np.nan for r in clima], dtype=float),
        "kp_max": np.array([r[2] if r[2] is not None else np.nan for r in clima], dtype=float),
        "bz_prom": np.array([r[3] if r[3] is not None else np.nan for r in clima], dtype=float),
        "bz_min": np.array([r[4] if r[4] is not None else np.nan for r in clima], dtype=float),
        "viento_avg": np.array([r[5] if r[5] is not None else np.nan for r in clima], dtype=float),
        "viento_max": np.array([r[6] if r[6] is not None else np.nan for r in clima], dtype=float),
        "proton_flux": np.array([r[7] if r[7] is not None else np.nan for r in clima], dtype=float),
        "prot_dens": np.array([r[8] if r[8] is not None else np.nan for r in clima], dtype=float),
    }

    # Máscaras de validez
    valid = {k: ~np.isnan(v) for k, v in vars_clima.items()}

    # Sismos
    sismos = c.execute(
        f"SELECT time_utc, mag FROM {TABLA_SISMOS} WHERE mag >= ? ORDER BY time_utc",
        (MAG_MIN,)).fetchall()
    sismos_dt = np.array([dt.datetime.strptime(r[0][:19], "%Y-%m-%d %H:%M:%S") for r in sismos], dtype='datetime64[s]')
    sismos_mag = np.array([r[1] for r in sismos])
    print(f"Sismos M≥{MAG_MIN}: {len(sismos_dt):,}")

    rng = random.Random(SEMILLA)
    años_disponibles = sorted(set(años_clima))

    parejas = {v: [] for v in vars_clima}
    paso = max(1, len(sismos_dt) // 400)

    for idx in range(0, len(sismos_dt), paso):
        t_sismo = sismos_dt[idx]
        año_sismo = int(t_sismo.astype('datetime64[Y]').astype(int) + 1970)
        doy = int((t_sismo - np.datetime64(f'{año_sismo}-01-01')).astype('timedelta64[D]').astype(int)) + 1

        años_control = [a for a in años_disponibles if a != año_sismo]
        if not años_control:
            continue

        # Buscar control estacional válido
        t_control = None
        for _ in range(50):
            año_c = rng.choice(años_control)
            diy_c = 366 if calendar.isleap(año_c) else 365
            doy_c = doy + rng.randint(-QUINCENA_D, QUINCENA_D)
            if doy_c < 1: doy_c += diy_c
            if doy_c > diy_c: doy_c -= diy_c
            try:
                t_c = np.datetime64(f'{año_c}-01-01') + np.timedelta64(doy_c - 1, 'D')
                t_c = t_c.astype('datetime64[s]')
                t_c = np.datetime64(f'{t_c.astype("datetime64[m]")}')  # truncar a minutos
                # Check rápido: datos válidos en ventana para TODAS las variables
                h_antes = (t_c - times_clima).astype('timedelta64[h]').astype(float)
                mask = (h_antes > 0) & (h_antes <= VENTANA_H)
                if not np.any(mask):
                    continue
                ok = True
                for var, v in vars_clima.items():
                    if not np.any(valid[var] & mask):
                        ok = False
                        break
                if ok:
                    t_control = t_c
                    break
            except (ValueError, OverflowError):
                continue

        if t_control is None:
            continue

        # Calcular pendientes
        for var, vals in vars_clima.items():
            ev = slope_from_times_values(times_clima[valid[var]], vals[valid[var]], t_sismo, VENTANA_H, N_BINS)
            ca = slope_from_times_values(times_clima[valid[var]], vals[valid[var]], t_control, VENTANA_H, N_BINS)
            if ev and ca:
                parejas[var].append((ev, ca))

        if len(parejas["kp_prom"]) > 0 and len(parejas["kp_prom"]) % 50 == 0:
            print(f"  ... {len(parejas['kp_prom'])} pares")

    print("\n=== RESULTADOS (control estacional) ===")
    for var in vars_clima:
        n = len(parejas[var])
        if n < 10:
            print(f"{var:12}: {n} pares (insuficiente)")
            continue
        se = np.array([p[0][0] for p in parejas[var]])
        sc = np.array([p[1][0] for p in parejas[var]])
        me = np.array([p[0][1] for p in parejas[var]])
        mc = np.array([p[1][1] for p in parejas[var]])
        d_slope = se.mean() - sc.mean()
        sd = np.std(np.concatenate([se, sc]), ddof=0) or 1e-12
        d_media = me.mean() - mc.mean()
        sd_m = np.std(np.concatenate([me, mc]), ddof=0) or 1e-12
        sig_s = " *" if abs(d_slope/sd) > 2 else ""
        sig_m = " *" if abs(d_media/sd_m) > 2 else ""
        print(f"{var:12}: n={n:4} slope_ev={se.mean():+.4f} slope_ca={sc.mean():+.4f} "
              f"dif={d_slope:+.4f} ({d_slope/sd:+.2f}σ){sig_s}  "
              f"media_ev={me.mean():.2f} media_ca={mc.mean():.2f} dif={d_media:+.2f} ({d_media/sd_m:+.2f}σ){sig_m}")

    if out_f is not None:
        sys.stdout.flush()
        sys.stdout = sys.__stdout__
        out_f.close()
        print(f"[output guardado en {args.output}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())