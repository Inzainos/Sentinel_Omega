#!/usr/bin/env python3
"""
Re-etiquetado de veredictos usando ventana Molchan estándar: 72h / 5° radio.

Este script:
1. Toma todas las predicciones registradas en TBL_JUEZ_AUDITORIA (vivas)
2. Las re-evalúa contra el catálogo USGS histórico (tbl_eventos_sismicos_fuente)
   usando ventana 72h y radio 5° euclidiano (estándar Molchan)
3. Genera una tabla nueva `tbl_veredictos_molchan_m{mag*10}` con etiquetas consistentes
4. Permite entrenar con labels correctos para Molchan gain > 1.0

Uso:
  python scripts/re_label_molchan.py [--dry-run] [--mag-threshold 5.5] [--log RUTA]

Historial (tuning P3, 2026-11-10): el CASE SQL colapsaba ACIERTO_CALMA a
ACIERTO en ambas columnas, lo que invertía el veredicto de ganancia (0.927x
"sin ganancia" con el bug vs 1.026x "ganancia marginal" correcto, re-derivado
con los conteos reales de tbl_veredictos_molchan_m55: ACIERTO 302,
ACIERTO_CALMA 1,404, FALLO 753, FALSO_POSITIVO 533; auditoría H-10, parte 2).
Corregido: ACIERTO_CALMA se preserva como ("sin eventos", "ACIERTO").
Default alineado al piso vigente MIN_MAGNITUD_FIRMA = 5.5 (antes 4.5, piso
viejo). --dry-run ahora calcula y muestra la ganancia sin escribir nada.
"""

import argparse
import logging
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # raíz del repo (antes: .../sentinel_omega, no resolvía el paquete)

DB_PATH = Path(__file__).resolve().parents[1] / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"

# Estándar Molchan
MOLCHAN_WINDOW_H = 72
MOLCHAN_RADIUS_DEG = 5.0
# Piso vigente MIN_MAGNITUD_FIRMA = 5.5 (entrenamiento.py:69). El default viejo
# 4.5 contaba como verdad eventos M4.5-5.49 que el muro ya trata como no
# exigibles (tuning P3 2026-11-10; H-10).
MAG_THRESHOLD = 5.5  # M>=5.5 para consistencia con la disciplina vigente

# Señales de ALERT del sistema
ALERT_SIGNALS = {"alert", "watch", "warning"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [RELABEL] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_predictions(conn):
    """Obtiene todas las predicciones vivas con sus zonas."""
    # TBL_JUEZ_AUDITORIA tiene las predicciones con detalles_json que incluye zonas
    rows = conn.execute("""
        SELECT id, timestamp, bot_name, prediccion, confianza, ventana_h, 
               detalles_json, fase
        FROM TBL_JUEZ_AUDITORIA 
        WHERE resultado != 'PENDIENTE' AND fase = 'viva'
        ORDER BY timestamp
    """).fetchall()
    return rows


def get_historical_events(conn, start_ts, end_ts, mag_threshold):
    """Obtiene eventos sísmicos M>=threshold del catálogo histórico en rango temporal."""
    # Usar tbl_eventos_sismicos_fuente que tiene eventos individuales USGS
    # Convertir timestamps a epoch para comparación
    start_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    end_str = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    rows = conn.execute("""
        SELECT usgs_id, time_utc, lat, lon, mag, depth_km, place
        FROM tbl_eventos_sismicos_fuente
        WHERE mag >= ? AND time_utc BETWEEN ? AND ?
        ORDER BY time_utc
    """, (mag_threshold, start_str, end_str)).fetchall()
    
    events = []
    for r in rows:
        # Parse time_utc to epoch
        try:
            dt = datetime.fromisoformat(r[1].replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            epoch = dt.timestamp()
        except Exception:
            continue
        events.append({
            "event_id": r[0],
            "epoch": epoch,
            "lat": r[2],
            "lon": r[3],
            "magnitude": r[4],
            "depth_km": r[5],
            "place": r[6]
        })
    return events


def extract_zones(detalles_json):
    """Extrae zonas (lat, lon) del detalles_json de la predicción."""
    if not detalles_json:
        return []
    try:
        import json
        data = json.loads(detalles_json)
        # Zonas pueden venir como "zonas" o "nodos" - estructura variable
        zonas_raw = data.get("zonas") or data.get("nodos") or []
        # Filtrar tuplas válidas (lat, lon)
        valid = []
        for z in zonas_raw:
            if isinstance(z, dict) and "lat" in z and "lon" in z:
                # Formato objeto: {"lat": 38.0, "lon": 142.0}
                lat, lon = float(z["lat"]), float(z["lon"])
            elif isinstance(z, (list, tuple)) and len(z) >= 2:
                # Formato tupla: [lat, lon] o (lat, lon)
                lat, lon = float(z[0]), float(z[1])
            else:
                continue
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                valid.append((lat, lon))
        return valid
    except Exception:
        return []


def eventos_en_ventana(eventos, pred_ts, zonas, ventana_h=MOLCHAN_WINDOW_H, radio_deg=MOLCHAN_RADIUS_DEG):
    """Eventos dentro de ventana temporal y (si hay zonas) radio euclidiano."""
    fin = pred_ts + ventana_h * 3600
    matches = []
    for ev in eventos:
        epoch = ev.get("epoch")
        if epoch is None or not (pred_ts <= epoch <= fin):
            continue
        if zonas:
            elat, elon = ev.get("lat"), ev.get("lon")
            if elat is None or elon is None:
                continue
            cerca = any(
                math.sqrt((elat - zlat) ** 2 + (elon - zlon) ** 2) <= radio_deg
                for zlat, zlon in zonas
            )
            if not cerca:
                continue
        matches.append(ev)
    return matches


def crear_tabla_veredictos(conn, mag_threshold):
    """Crea tabla para veredictos re-etiquetados Molchan."""
    table_name = f"tbl_veredictos_molchan_m{int(mag_threshold*10)}"
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            juez_id INTEGER NOT NULL,           -- referencia a TBL_JUEZ_AUDITORIA
            timestamp REAL NOT NULL,            -- timestamp de la predicción
            bot_name TEXT NOT NULL,
            prediccion TEXT NOT NULL,
            confianza REAL,
            ventana_h INTEGER DEFAULT 72,
            radio_deg REAL DEFAULT 5.0,
            mag_threshold REAL DEFAULT {mag_threshold},
            -- Zonas usadas para evaluación
            zonas_json TEXT,                    -- JSON con [(lat, lon), ...]
            -- Ground truth
            n_eventos INTEGER DEFAULT 0,
            max_magnitude REAL,
            evento_cercano TEXT,                -- descripción del evento más cercano
            -- Veredicto Molchan
            predijo_evento INTEGER NOT NULL,    -- 1 si predicción en ALERT_SIGNALS
            evento_ocurrio INTEGER NOT NULL,    -- 1 si hubo evento en ventana/radio
            resultado TEXT NOT NULL,            -- ACIERTO, FALLO, FALSO_POSITIVO, ACIERTO_CALMA
            -- Métricas
            distancia_min_deg REAL,             -- distancia mínima a evento (si hay zonas)
            creado_at TEXT DEFAULT (datetime('now')),
            UNIQUE(juez_id)
        )
    """)
    # Índices
    table_name = f"tbl_veredictos_molchan_m{int(mag_threshold*10)}"
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_veredictos_molchan_bot ON {table_name}(bot_name)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_veredictos_molchan_ts ON {table_name}(timestamp)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_veredictos_molchan_res ON {table_name}(resultado)")
    conn.commit()
    return table_name


def molchan_rows_desde_stats(stats):
    """Construye las filas (verdad, resultado) para evaluar_veredictos desde
    los conteos en memoria. ACIERTO_CALMA se preserva como
    ("sin eventos", "ACIERTO"): una calma correcta NO es un evento detectado.
    (Antes el CASE SQL lo colapsaba a ("evento", "ACIERTO") e invertía la
    ganancia: 0.927x con bug vs 1.026x correcto en m55.)"""
    filas = []
    filas += [("evento", "ACIERTO")] * stats.get("ACIERTO", 0)
    filas += [("sin eventos", "FALSO_POSITIVO")] * stats.get("FALSO_POSITIVO", 0)
    filas += [("evento", "FALLO")] * stats.get("FALLO", 0)
    filas += [("sin eventos", "ACIERTO")] * stats.get("ACIERTO_CALMA", 0)
    return filas


def loguear_ganancia(molchan_rows, titulo="MOLCHAN GAIN CON NUEVOS LABELS"):
    """Calcula e imprime la ganancia Molchan; devuelve el resultado o None."""
    from sentinel_omega.core.precursor.baseline import evaluar_veredictos
    if not molchan_rows:
        logger.warning("Sin filas para evaluar ganancia Molchan")
        return None
    m = evaluar_veredictos(molchan_rows)
    logger.info(f"\n=== {titulo} ===")
    logger.info(f"Ventanas: {m.ventanas}")
    logger.info(f"Con evento: {m.con_evento} | Detectados: {m.detectados} | "
                f"Alarmadas: {m.alarmas} | Fallos: {m.fallos} | "
                f"Falsos positivos: {m.falsos_positivos}")
    logger.info(f"Ganancia: {m.ganancia:.3f}x")
    logger.info(f"Precisión: {m.precision:.4f}")
    logger.info(f"Tasa base: {m.tasa_base:.4f}")
    logger.info(f"Detección: {m.deteccion:.4f}")
    logger.info(f"Veredicto: {m.veredicto}")
    return m


def main():
    parser = argparse.ArgumentParser(description="Re-etiquetado Molchan 72h/5°")
    parser.add_argument("--dry-run", action="store_true", help="No escribir en BD (solo lectura; calcula conteos y ganancia)")
    parser.add_argument("--ventana-h", type=int, default=MOLCHAN_WINDOW_H, help="Ventana en horas (default 72)")
    parser.add_argument("--radio-deg", type=float, default=MOLCHAN_RADIUS_DEG, help="Radio en grados (default 5.0)")
    parser.add_argument("--mag-threshold", type=float, default=MAG_THRESHOLD, help="Umbral magnitud (default 5.5, piso vigente)")
    parser.add_argument("--log", default=None, help="Archivo de log (default: estado/re_label_molchan_AAAAMMDD-HHMMSS.log)")
    args = parser.parse_args()

    if args.log is None:
        args.log = str(Path(__file__).resolve().parents[1] / "estado" /
                       f"re_label_molchan_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.log")
    _fh = logging.FileHandler(args.log, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [RELABEL] %(levelname)s %(message)s"))
    logger.addHandler(_fh)
    logger.info(f"Log de esta corrida: {args.log}")

    # --dry-run abre la DB en modo solo lectura: garantiza que no escribe nada.
    if args.dry_run:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=60)
    else:
        conn = sqlite3.connect(str(DB_PATH), timeout=60)
    try:
        if not args.dry_run:
            table_name = crear_tabla_veredictos(conn, args.mag_threshold)

        # 1. Obtener predicciones vivas
        preds = get_predictions(conn)
        logger.info(f"Predicciones vivas a re-evaluar: {len(preds)}")

        # 2. Determinar rango temporal para eventos históricos
        if preds:
            min_ts = min(p[1] for p in preds)
            max_ts = max(p[1] for p in preds) + args.ventana_h * 3600
        else:
            logger.warning("No hay predicciones para procesar")
            return 0

        # 3. Cargar eventos históricos M>=threshold en ventana extendida
        eventos = get_historical_events(conn, min_ts, max_ts, args.mag_threshold)
        logger.info(f"Eventos históricos M>={args.mag_threshold} en rango: {len(eventos)}")

        # 4. Procesar cada predicción
        stats = {"ACIERTO": 0, "FALLO": 0, "FALSO_POSITIVO": 0, "ACIERTO_CALMA": 0}
        processed = 0

        for juez_id, pred_ts, bot_name, prediccion, confianza, ventana_h, detalles_json, fase in preds:
            zonas = extract_zones(detalles_json)
            
            # Evaluar con estándar Molchan
            matches = eventos_en_ventana(
                eventos, pred_ts, zonas,
                ventana_h=args.ventana_h, radio_deg=args.radio_deg
            )
            
            evento_ocurrio = len(matches) > 0
            predijo_evento = str(prediccion).lower() in ALERT_SIGNALS

            if predijo_evento and evento_ocurrio:
                resultado = "ACIERTO"
            elif predijo_evento and not evento_ocurrio:
                resultado = "FALSO_POSITIVO"
            elif not predijo_evento and evento_ocurrio:
                resultado = "FALLO"
            else:
                resultado = "ACIERTO_CALMA"  # calma predicha, calma real

            # Métricas adicionales
            max_mag = max((m["magnitude"] for m in matches), default=None)
            n_eventos = len(matches)
            
            # Evento más cercano para descripción
            evento_cercano = ""
            dist_min = None
            if matches:
                # Ordenar por distancia a zonas si hay zonas, sino por magnitud
                if zonas:
                    def dist_to_zones(ev):
                        elat, elon = ev["lat"], ev["lon"]
                        return min(math.sqrt((elat - zl)**2 + (elon - zn)**2) for zl, zn in zonas)
                    matches.sort(key=dist_to_zones)
                    dist_min = dist_to_zones(matches[0])
                else:
                    matches.sort(key=lambda m: -m["magnitude"])
                
                ev = matches[0]
                evento_cercano = f"M{ev['magnitude']:.1f} {ev['place'] or 'desconocido'}"

            if not args.dry_run:
                import json
                conn.execute(f"""
                    INSERT OR REPLACE INTO {table_name}
                    (juez_id, timestamp, bot_name, prediccion, confianza, ventana_h, radio_deg,
                     mag_threshold, zonas_json, n_eventos, max_magnitude, evento_cercano,
                     predijo_evento, evento_ocurrio, resultado, distancia_min_deg)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    juez_id, pred_ts, bot_name, prediccion, confianza,
                    args.ventana_h, args.radio_deg, args.mag_threshold,
                    json.dumps(zonas), n_eventos, max_mag, evento_cercano,
                    int(predijo_evento), int(evento_ocurrio), resultado, dist_min
                ))

            stats[resultado] = stats.get(resultado, 0) + 1
            processed += 1

            if processed % 500 == 0:
                logger.info(f"Procesados {processed}/{len(preds)}...")

        if not args.dry_run:
            conn.commit()

        logger.info(f"=== RESUMEN RE-ETIQUETADO (72h/5°, M>={args.mag_threshold}) ===")
        for k, v in stats.items():
            logger.info(f"  {k}: {v}")
        logger.info(f"  Total: {sum(stats.values())}")

        # Calcular Molchan gain con nuevos labels. En --dry-run se calcula
        # desde los conteos en memoria (sin tocar la DB); en modo real, desde
        # la tabla recién escrita, leyendo predijo_evento/evento_ocurrio
        # directamente — el CASE viejo colapsaba ACIERTO_CALMA a ACIERTO.
        if args.dry_run:
            loguear_ganancia(molchan_rows_desde_stats(stats),
                             "MOLCHAN GAIN CON NUEVOS LABELS (--dry-run, sin escritura)")
        else:
            rows = conn.execute(f"""
                SELECT predijo_evento, evento_ocurrio FROM {table_name}
            """).fetchall()
            molchan_rows = []
            for predijo, ocurrio in rows:
                if predijo == 1 and ocurrio == 1:
                    molchan_rows.append(("evento", "ACIERTO"))
                elif predijo == 1 and ocurrio == 0:
                    molchan_rows.append(("sin eventos", "FALSO_POSITIVO"))
                elif predijo == 0 and ocurrio == 1:
                    molchan_rows.append(("evento", "FALLO"))
                else:
                    molchan_rows.append(("sin eventos", "ACIERTO"))  # ACIERTO_CALMA
            loguear_ganancia(molchan_rows)

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())