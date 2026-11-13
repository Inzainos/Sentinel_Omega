"""
fix_reporte_muro.py — parche de la SECCIÓN DEL MURO en el reporte Padre.

NO arregla el muro (muro_cinco_eventos.py / entrenamiento.py / tests): cambia
la fuente de activación de muros en deploy/generar_reporte.py, de
`precursors_activos` (confianzas del ciclo) a la última fila de
TBL_MURO_EVENTOS, y el texto "Sin señales activas" por
"Sin señales activas (calma actual)".

Historial (tuning P3, 2026-11-10): había 3 copias (fix_muro.py, fix_muro2.py
— lógica idéntica — y fix_muro3.py — variante regex con old_section sin uso).
El parche YA estaba aplicado en vivo (generar_reporte.py mtime 2026-11-08
16:28, diff +67/-3); las otras dos eran no-ops silenciosos que imprimían
"Fixed!" sin reemplazar nada. Se archivan las 3 y sobrevive esta, renombrada
para no engañar, con GUARDA: si la sección vieja ya no existe, sale con
código 1 SIN escribir nada (antes imprimía "Fixed!" incondicional).
"""
import re
import sys

# Read the file
with open('/home/deamon/Sentinel_Omega/deploy/generar_reporte.py', 'r') as f:
    content = f.read()

# Find and replace the problematic section
old_section = '''        # Check which precursors are active from current cycle
        precursors_activos = {}
        if detections:
            for d in detections:
                precursors_activos[d.tipo.value] = d.confidence

        # Check muro status from latest TBL_MURO_EVENTOS
        muro_row = conn.execute(
            "SELECT wall_geofisico, wall_atmosferico, wall_oceanico, wall_solar, wall_financiero "
            "FROM TBL_MURO_EVENTOS ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

        if muro_row:
            muro_walls_list = ["GEOFÍSICO", "ATMOSFÉRICO", "OCEÁNICO", "SOLAR/GEOMAGNÉTICO", "FINANCIERO/SOCIAL"]
            for i, wall_name in enumerate(muro_walls_list):
                if muro_row[i]:
                    muro_walls[wall_name]["activo"] = True

        # Add active signals to each wall's detail
        for wall_name, info in muro_walls.items():
            for signal in info["señales"]:
                if signal in precursors_activos:
                    info["activo"] = True
                    info["detalle"].append(f"{signal} ({precursors_activos[signal]:.0%})")

        lineas += ["## 🧱 Muro de los 5 frentes — detalle", ""]

        for wall_name, info in muro_walls.items():
            estado = "✅ ACTIVO" if info["activo"] else "⬜ INACTIVO"
            lineas.append(f"### {wall_name} {estado}")
            if info["detalle"]:
                for d in info["detalle"]:
                    lineas.append(f"- `{d}`")
            else:
                lineas.append("- Sin señales activas")

        lineas += ["", "---", ""]

    except sqlite3.OperationalError:
        pass

    # ── 📈 Operación reciente: hoy vs cómo solía estar ──'''

new_section = '''        # Check muro status from latest TBL_MURO_EVENTOS
        muro_row = conn.execute(
            "SELECT wall_geofisico, wall_atmosferico, wall_oceanico, wall_solar, wall_financiero "
            "FROM TBL_MURO_EVENTOS ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

        if muro_row:
            muro_walls_list = ["GEOFÍSICO", "ATMOSFÉRICO", "OCEÁNICO", "SOLAR/GEOMAGNÉTICO", "FINANCIERO/SOCIAL"]
            for i, wall_name in enumerate(muro_walls_list):
                if muro_row[i]:
                    muro_walls[wall_name]["activo"] = True
                    muro_walls[wall_name]["detalle"].append(f"BD: {muro_row[i]}")

        lineas += ["## 🧱 Muro de los 5 frentes — detalle", ""]

        for wall_name, info in muro_walls.items():
            estado = "✅ ACTIVO" if info["activo"] else "⬜ INACTIVO"
            lineas.append(f"### {wall_name} {estado}")
            if info["detalle"]:
                for d in info["detalle"]:
                    lineas.append(f"- `{d}`")
            else:
                lineas.append("- Sin señales activas (calma actual)")
            lineas.append("")

        lineas += ["", "---", ""]

    except sqlite3.OperationalError:
        pass

    # ── 📈 Operación reciente: hoy vs cómo solía estar ──'''

if old_section not in content:
    print("ERROR: la sección vieja ya no está en generar_reporte.py "
          "(parche ya aplicado o sección cambiada). Sin reemplazo, sin escritura.",
          file=sys.stderr)
    sys.exit(1)

content = content.replace(
    old_section,
    new_section
)

# Write the fixed file
with open('/home/deamon/Sentinel_Omega/deploy/generar_reporte.py', 'w') as f:
    f.write(content)

print("Fixed!")