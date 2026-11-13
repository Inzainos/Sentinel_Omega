import re

with open('/home/deamon/Sentinel_Omega/deploy/generar_reporte.py', 'r') as f:
    content = f.read()

# Replace the specific problematic section using regex
old_section = r'''        # Check which precursors are active from current cycle
        precursors_activos = \{\}
        if detections:
            for d in detections:
                precursors_activos\[d\.tipo\.value\] = d\.confidence

        # Check muro status from latest TBL_MURO_EVENTOS
        muro_row = conn\.execute\(
            "SELECT wall_geofisico, wall_atmosferico, wall_oceanico, wall_solar, wall_financiero "
            "FROM TBL_MURO_EVENTOS ORDER BY timestamp DESC LIMIT 1"
        \)\.fetchone\(\)

        if muro_row:
            muro_walls_list = \["GEOFÍSICO", "ATMOSFÉRICO", "OCEÁNICO", "SOLAR/GEOMAGNÉTICO", "FINANCIERO/SOCIAL"\]
            for i, wall_name in enumerate\(muro_walls_list\):
                if muro_row\[i\]:
                    muro_walls\[wall_name\]\["activo"\] = True

        # Add active signals to each wall's detail
        for wall_name, info in muro_walls\.items\(\):
            for signal in info\["señales"\]:
                if signal in precursors_activos:
                    info\["activo"\] = True
                    info\["detalle"\]\.append\(f"{signal} \({precursors_activos\[signal\]:.0%}\)"\)

        lineas \+= \["## 🧱 Muro de los 5 frentes — detalle", ""\]

        for wall_name, info in muro_walls\.items\(\):
            estado = "✅ ACTIVO" if info\["activo"\] else "⬜ INACTIVO"
            lineas\.append\(f"### {wall_name} {estado}"\)
            if info\["detalle"\]:
                for d in info\["detalle"\]:
                    lineas\.append\(f"- `{d}`"\)
            else:
                lineas\.append\("- Sin señales activas"\)

        lineas \+= \["", "---", ""\]

    except sqlite3\.OperationalError:
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

# Use DOTALL flag to match across multiple lines
content = re.sub(
    r'# Check which precursors are active from current cycle\s*\n.*?# ── 📈 Operación reciente: hoy vs cómo solía estar ──',
    new_section,
    content,
    flags=re.DOTALL
)

# Write the fixed file
with open('/home/deamon/Sentinel_Omega/deploy/generar_reporte.py', 'w') as f:
    f.write(content)

print("Fixed!")