#!/usr/bin/env python3
"""
Backtest completo: re-ejecuta el pipeline simulando fallback Schumann.

Compara:
1. Pipeline con datos Tomsk reales (histórico)
2. Pipeline con ResonanceOne fallback en días sin Tomsk

Uso:
  python scripts/backtest_pipeline_molchan.py --desde 2026-10-26 --hasta 2026-11-05 --output estado/backtest_pipeline_2026-11-10.txt

NOTA tuning P3 2026-11-10: la comparación A/B por RE-EJECUCIÓN del pipeline
(run_pipeline_with_schumann + evaluate_molchan_from_predictions) se BORRÓ
por inviable tal como estaba diseñada: el monkey-patch solo sobrescribía
el valor de HOY (no cada día del rango), el pipeline usa ventanas de 30-90
días con estado y fuentes en vivo, y re-correrlo por cada día histórico no
reconstruye las predicciones de ese día (además escribiría/consultaría en
vivo). La comparación real es la estratificación observacional de los
veredictos ya resueltos por fuente Schumann del día (implementada en
backtest_schumann_molchan.py --compare; aquí se reproduce el mismo resumen
para que este script sea autocontenido). Añadidos: --db, apertura mode=ro
(solo lectura garantizada), --output (Tee a archivo). El import de
GeodynamicPipeline se eliminó con el código muerto (este script ya no
ejecuta el pipeline, solo lee veredictos).
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

# Raíz del repo en sys.path para importar el paquete sentinel_omega
# (el viejo insertaba .../sentinel_omega, que NO resuelve el paquete:
# el script ni siquiera importaba sin PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel_omega.core.precursor.baseline import evaluar_veredictos

DB_PATH = Path(__file__).resolve().parents[1] / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"

# Valor de fallback ResonanceOne típico (basado en observaciones)
RESONANCEONE_FALLBACK = 19.5


def get_schumann_diario(conn, start, end):
    return conn.execute(
        "SELECT fecha, actividad, fuente FROM tbl_schumann_diario "
        "WHERE fecha BETWEEN ? AND ? ORDER BY fecha",
        (start, end)
    ).fetchall()


def comparar_estratos(viva_rows, schumann_data):
    """
    Estratifica los veredictos ya resueltos por la fuente Schumann del día
    (Tomsk real vs fallback/sin dato) y calcula la ganancia Molchan de cada
    estrato. Ver backtest_schumann_molchan.py para la justificación.
    """
    fuente_por_dia = {f: fu for f, a, fu in schumann_data}
    estratos = {"tomsk": [], "fallback": []}
    for ts, verdad, resultado in viva_rows:
        fecha = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        estrato = "tomsk" if fuente_por_dia.get(fecha) == "tomsk_wpc_corte_diario" else "fallback"
        estratos[estrato].append((verdad, resultado))
    return {k: evaluar_veredictos(v) for k, v in estratos.items()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--desde", required=True, help="YYYY-MM-DD")
    p.add_argument("--hasta", required=True, help="YYYY-MM-DD")
    p.add_argument("--fallback", type=float, default=RESONANCEONE_FALLBACK)
    p.add_argument("--db", default=str(DB_PATH), help="Ruta a la DB SQLite (default: DB viva)")
    p.add_argument("--output", default=None, help="Archivo donde guardar el resultado (además de stdout)")
    args = p.parse_args()

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

    start_ts = datetime.strptime(args.desde, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    end_ts = datetime.strptime(args.hasta, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc).timestamp()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=30)

    # 1. Obtener datos Schumann reales
    sch_data = get_schumann_diario(conn, args.desde, args.hasta)
    print(f"Días con datos Schumann: {len(sch_data)}")
    
    # Identificar días sin Tomsk (gap)
    fechas_con_dato = {f for f, a, fu in sch_data if a is not None}
    print(f"Fechas con Tomsk: {sorted(fechas_con_dato)}")
    
    # 2. Veredictos del Juez en el rango
    viva = conn.execute(
        "SELECT timestamp, verdad, resultado FROM viva_real "
        "WHERE COALESCE(en_vivo,1)=1 AND resultado != 'PENDIENTE' "
        "AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
        (start_ts, end_ts)
    ).fetchall()
    
    print(f"\nVeredictos viva_real: {len(viva)}")
    
    # 3. Evaluar Molchan actual
    veredictos = [(v, r) for _, v, r in viva]
    molchan = evaluar_veredictos(veredictos)
    print(f"\n=== MOLCHAN BASELINE ===")
    print(f"Ganancia: {molchan.ganancia:.3f}x")
    print(f"Precisión: {molchan.precision:.4f}")
    print(f"Tasa base: {molchan.tasa_base:.4f}")
    print(f"Veredicto: {molchan.veredicto}")
    
    # 4. Análisis por día: correlación Schumann vs precision
    print(f"\n=== ANÁLISIS DÍA A DÍA ===")
    for fecha, act, fu in sch_data:
        if act is None:
            continue
        # Veredictos de ese día
        fecha_start = datetime.strptime(fecha, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        fecha_end = fecha_start + 86400
        dia_veredictos = [v for v in viva if fecha_start <= v[0] < fecha_end]
        
        if dia_veredictos:
            vr = [(v, r) for _, v, r in dia_veredictos]
            m = evaluar_veredictos(vr)
            gain_str = f"{m.ganancia:.2f}x" if m.ganancia else "None"
            prec_str = f"{m.precision:.3f}" if m.precision else "None"
            base_str = f"{m.tasa_base:.3f}" if m.tasa_base else "None"
            print(f"  {fecha}: sch={act:.1f}% fuente={fu} gain={gain_str} prec={prec_str} base={base_str} (n={m.ventanas})")

    # 5. Días faltantes (gap Nov 2-5)
    print(f"\n=== DÍAS SIN TOMKS (gap) ===")
    from datetime import timedelta
    all_dates = set()
    current = datetime.strptime(args.desde, "%Y-%m-%d").date()
    end = datetime.strptime(args.hasta, "%Y-%m-%d").date()
    while current <= end:
        all_dates.add(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    missing = all_dates - fechas_con_dato
    for fecha in sorted(missing):
        print(f"  {fecha}: SIN DATO - fallback would use {args.fallback}%")

    # 6. Comparación Tomsk vs fallback (estratos de veredictos ya resueltos)
    print(f"\n=== COMPARACIÓN TOMSK vs FALLBACK (observacional) ===")
    print("Veredictos ya resueltos, estratificados por la fuente Schumann del día.")
    comp = comparar_estratos(viva, sch_data)
    for estrato in ("tomsk", "fallback"):
        m = comp[estrato]
        if m is None:
            print(f"  {estrato}: sin veredictos en el rango (sin ganancia que medir)")
            continue
        g = f"{m.ganancia:.3f}x" if m.ganancia is not None else "None"
        pr = f"{m.precision:.4f}" if m.precision is not None else "None"
        print(f"  {estrato}: n={m.ventanas} con_evento={m.con_evento} alarmas={m.alarmas} "
              f"detectados={m.detectados} prec={pr} base={m.tasa_base:.4f} ganancia={g} "
              f"veredicto={m.veredicto}")
    mt, mf = comp["tomsk"], comp["fallback"]
    if mt is not None and mf is not None and mt.ganancia is not None and mf.ganancia is not None:
        print(f"  lift Tomsk/fallback: {mt.ganancia / mf.ganancia:.3f}x "
              f"(>1 = los días con Tomsk real rindieron mejor)")

    conn.close()
    if out_f is not None:
        sys.stdout.flush()
        sys.stdout = sys.__stdout__
        out_f.close()
        print(f"[output guardado en {args.output}]")


if __name__ == "__main__":
    main()