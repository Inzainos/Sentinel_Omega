#!/usr/bin/env python3
"""
Backtest Molchan gain: Tomsk vs ResonanceOne fallback.

Compara la ganancia de Molchan usando:
1. Datos Tomsk reales (corte diario histórico)
2. Simulación con ResonanceOne fallback para días donde Tomsk falló

Uso:
  python scripts/backtest_schumann_molchan.py --desde 2026-10-01 --hasta 2026-11-06 --compare --output estado/backtest_schumann_2026-11-10.txt

NOTA tuning P3 2026-11-10 (la comparación REAL, antes --compare no hacía nada):
la comparación NO re-ejecuta el pipeline por día (inviable: el pipeline es
con estado, usa ventanas de 30-90 días y fuentes en vivo; re-correrlo por
cada día histórico no reconstruye las predicciones de ese día). La
comparación real es OBSERVACIONAL: los veredictos ya resueltos por el Juez
se estratifican por la fuente Schumann del día en que cayeron (Tomsk real
vs fallback/sin dato) y se calcula la ganancia Molchan de cada estrato con
evaluar_veredictos. Eso responde "¿los días con Tomsk real rindieron mejor
que los días con fallback?" con los datos que existen, sin inventar
predicciones. La función muerta build_veredictos_with_schumann (devolvía los
veredictos sin tocar) se borró. Añadidos: --db (default: DB viva), apertura
en mode=ro (solo lectura garantizada) y --output (Tee a archivo).
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

# Fuentes Schumann que cuentan como "fallback / sin dato real" (vs Tomsk real).
FUENTES_FALLBACK = ("tomsk_fallido", "resonanceone_backup", "sin_dato_historico")


def get_schumann_diario(conn, start, end):
    """Obtiene corte diario de Schumann en rango de fechas."""
    return conn.execute(
        "SELECT fecha, actividad, fuente FROM tbl_schumann_diario "
        "WHERE fecha BETWEEN ? AND ? ORDER BY fecha",
        (start, end)
    ).fetchall()


def get_viva_real(conn, start, end):
    """Obtiene veredictos del Juez en rango de fechas."""
    return conn.execute(
        "SELECT timestamp, verdad, resultado FROM viva_real "
        "WHERE COALESCE(en_vivo,1)=1 AND resultado != 'PENDIENTE' "
        "AND timestamp >= ? AND timestamp <= ? "
        "ORDER BY timestamp",
        (start, end)
    ).fetchall()


def simulate_with_fallback(schumann_data, fallback_value=19.5):
    """
    Simula datos con fallback: días con Tomsk real usan Tomsk,
    días sin Tomsk (actividad IS NULL o fuente=tomsk_fallido) usan fallback.
    """
    simulated = {}
    for fecha, actividad, fuente in schumann_data:
        if actividad is not None and fuente == "tomsk_wpc_corte_diario":
            simulated[fecha] = actividad
        else:
            simulated[fecha] = fallback_value  # ResonanceOne típico
    return simulated


def comparar_estratos(viva_rows, schumann_data):
    """
    Comparación REAL (observacional) Tomsk vs fallback.

    Estratifica los veredictos ya resueltos por la fuente Schumann del día
    en que cayeron y calcula la ganancia Molchan de cada estrato. Un estrato
    sin veredictos se reporta como tal (no se inventa ganancia).
    Retorna dict {estrato: VeredictosResult | None}.
    """
    fuente_por_dia = {f: fu for f, a, fu in schumann_data}
    estratos = {"tomsk": [], "fallback": []}
    for ts, verdad, resultado in viva_rows:
        fecha = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        estrato = "tomsk" if fuente_por_dia.get(fecha) == "tomsk_wpc_corte_diario" else "fallback"
        estratos[estrato].append((verdad, resultado))
    return {k: evaluar_veredictos(v) for k, v in estratos.items()}


def analyze_schumann_impact(conn, start_ts, end_ts, schumann_simulado):
    """
    Analiza cómo el valor de Schumann en cada día afecta a las predicciones
    de los veredictos que cayeron en ese día.
    """
    # Obtener veredictos con su timestamp y el Schumann del día
    viva = get_viva_real(conn, start_ts, end_ts)
    
    # Agrupar por día y ver estadísticas
    from collections import defaultdict
    dia_stats = defaultdict(lambda: {'total': 0, 'con_evento': 0, 'alarmas': 0, 'detectados': 0})
    
    for ts, verdad, resultado in viva:
        fecha = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        sch_val = schumann_simulado.get(fecha, None)
        
        dia_stats[fecha]['total'] += 1
        if not str(verdad or "").startswith("sin eventos"):
            dia_stats[fecha]['con_evento'] += 1
        if resultado in ("FALSO_POSITIVO", "ACIERTO"):
            dia_stats[fecha]['alarmas'] += 1
        if resultado == "ACIERTO":
            dia_stats[fecha]['detectados'] += 1
        dia_stats[fecha]['schumann'] = sch_val
    
    return dia_stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--desde", required=True, help="YYYY-MM-DD")
    p.add_argument("--hasta", required=True, help="YYYY-MM-DD")
    p.add_argument("--fallback-value", type=float, default=19.5,
                   help="Actividad %% para fallback (default ResonanceOne backup)")
    p.add_argument("--compare", action="store_true",
                   help="Comparar Tomsk real vs simulado con fallback en días sin Tomsk")
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

    # 1. Obtener datos Schumann diarios
    sch_data = get_schumann_diario(conn, args.desde, args.hasta)
    print(f"Días Schumann en rango: {len(sch_data)}")
    for fecha, act, fu in sch_data:
        print(f"  {fecha}: act={act} fuente={fu}")

    # 2. Simular con fallback
    sch_sim = simulate_with_fallback(sch_data, args.fallback_value)
    print(f"\nSimulación con fallback={args.fallback_value}%:")
    for fecha in sorted(sch_sim.keys()):
        original = next((a for f, a, _ in sch_data if f == fecha), None)
        print(f"  {fecha}: original={original} -> simulado={sch_sim[fecha]}")

    # 3. Obtener veredictos del Juez
    viva = get_viva_real(conn, start_ts, end_ts)
    print(f"\nVeredictos viva_real: {len(viva)}")

    # 4. Evaluar Molchan actual (baseline)
    veredictos = [(v, r) for _, v, r in viva]
    molchan = evaluar_veredictos(veredictos)
    print(f"\n=== MOLCHAN ACTUAL (baseline) ===")
    print(f"Ventanas: {molchan.ventanas}")
    print(f"Con evento: {molchan.con_evento}")
    print(f"Alarmas: {molchan.alarmas}")
    print(f"Detectados: {molchan.detectados}")
    print(f"Precisión: {molchan.precision:.4f}")
    print(f"Tasa base: {molchan.tasa_base:.4f}")
    print(f"Ganancia: {molchan.ganancia:.3f}x")
    print(f"Veredicto: {molchan.veredicto}")

    # 5. Análisis por fuente Schumann
    print(f"\n=== ANÁLISIS POR FUENTE ===")
    tomsk_days = [f for f, a, fu in sch_data if fu == "tomsk_wpc_corte_diario"]
    fallback_days = [f for f, a, fu in sch_data if fu in ("tomsk_fallido", "resonanceone_backup")]
    print(f"Días con Tomsk real: {len(tomsk_days)}")
    print(f"Días con fallback: {len(fallback_days)}")

    # 6. Análisis de impacto por día
    print(f"\n=== IMPACTO SCHUMANN POR DÍA ===")
    dia_stats = analyze_schumann_impact(conn, start_ts, end_ts, sch_sim)
    
    for fecha in sorted(dia_stats.keys()):
        s = dia_stats[fecha]
        if s['total'] > 0:
            precision = s['detectados'] / s['alarmas'] if s['alarmas'] > 0 else 0
            tasa_base_dia = s['con_evento'] / s['total']
            ganancia = (precision / tasa_base_dia) if (precision > 0 and tasa_base_dia > 0) else None
            print(f"  {fecha}: sch={s['schumann']} total={s['total']} ev={s['con_evento']} "
                  f"alar={s['alarmas']} det={s['detectados']} "
                  f"prec={precision:.3f} base={tasa_base_dia:.3f} gain={ganancia:.3f}x" if ganancia else
                  f"  {fecha}: sch={s['schumann']} total={s['total']} ev={s['con_evento']} "
                  f"alar={s['alarmas']} det={s['detectados']}")

    # 7. Comparación real Tomsk vs fallback (--compare)
    if args.compare:
        print(f"\n=== COMPARACIÓN TOMSK vs FALLBACK (observacional) ===")
        print("Veredictos ya resueltos, estratificados por la fuente Schumann del día.")
        print("No es un re-run del pipeline: es lo que los datos existentes permiten medir.")
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