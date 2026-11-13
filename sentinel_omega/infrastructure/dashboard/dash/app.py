"""
Sentinel Omega Dashboard - Dash Plotly
17 tabs specification from 06_DASHBOARD_WEB.txt
Dark theme #0a0a0a, port 8128, basic auth via DASH_USER/DASH_PASS
"""
import os
from pathlib import Path
import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta

import dash
from dash import dcc, html
import dash_auth
import dash_table
import plotly.express as px
import plotly.graph_objects as go
import psutil

# --- Auth ---
DASH_USER = os.getenv("DASH_USER", "capitan")
DASH_PASS = os.getenv("DASH_PASS", "omega2026")
VALID_USERS = {DASH_USER: DASH_PASS}

# --- DB path ---
BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "data" / "SENTINEL_OMEGA_PRO.db"

def get_conn():
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

def query_df(sql, params=()):
    try:
        conn = get_conn()
        if conn is None:
            return pd.DataFrame()
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def empty_state(title="Sin datos"):
    return html.Div([html.H3(title, className="accent"), html.Div("Tabla no encontrada o sin registros.", className="card")])

# --- App ---
app = dash.Dash(__name__, suppress_callback_exceptions=True, title="Sentinel Omega")
server = app.server

dark_css = """
:root {
  --bg:#0a0a0a; --bg-elev:#0f111a; --card:rgba(26,26,46,0.7);
  --accent-cyan:#00f2fe; --accent-violet:#7a5cff; --accent-amber:#ffb020; --accent-red:#ff4d4d;
  --text:#e8eef7; --muted:#9aa4b2; --border:rgba(0,242,254,0.15);
  --cream:rgba(26,26,46,0.85);
}
html,body{height:100%}
body{
  background-color:var(--bg);
  color:var(--text);
  font-family:'Inter','Consolas',monospace;
  margin:0;
  overflow-x:hidden;
}
body::before{
  content:""; position:fixed; inset:-20%; z-index:-2;
  background:
    radial-gradient(800px 500px at 15% -10%, rgba(74,58,122,0.06), transparent 60%),
    radial-gradient(900px 600px at 85% 0%, rgba(10,90,90,0.05), transparent 60%),
    radial-gradient(700px 500px at 50% 120%, rgba(139,106,42,0.04), transparent 60%),
    var(--bg);
  animation:bg-drift 60s ease-in-out infinite alternate;
}
@keyframes bg-drift{0%{transform:translateY(0) scale(1)}100%{transform:translateY(-2%) scale(1.03)}}
.cymatic-grid{
  position:fixed; inset:0; z-index:-1; opacity:.06; pointer-events:none;
  background-image:
    repeating-radial-gradient(circle at 1px 1px, rgba(0,242,254,.35) 0 1px, transparent 1px 24px),
    repeating-linear-gradient(0deg, rgba(122,92,255,.15) 0 1px, transparent 1px 24px);
  animation:cymatic-pulse 18s linear infinite;
}
@keyframes cymatic-pulse{0%{transform:translateZ(0) rotate(0deg)}100%{transform:translateZ(0) rotate(1deg)}}
#main-container{background:linear-gradient(180deg, var(--bg), var(--bg-elev)); min-height:100vh; padding:24px 20px 40px}
.header{
  display:flex; align-items:center; justify-content:space-between;
  background:linear-gradient(180deg, var(--bg-elev), var(--bg));
  border:1px solid var(--border); border-radius:16px; padding:14px 18px; margin-bottom:20px;
  backdrop-filter: blur(12px) saturate(140%); box-shadow:0 8px 30px rgba(0,0,0,.08), inset 0 1px 0 rgba(255,255,255,.8);
}
.logo{font-weight:800; letter-spacing:.5px; color:var(--text); display:flex; align-items:center; gap:10px}
.logo-mark{width:28px; height:28px; border-radius:8px; background:conic-gradient(from 0deg, var(--accent-cyan), var(--accent-violet), var(--accent-cyan)); box-shadow:0 0 18px rgba(0,242,254,.4); animation:spin-slow 30s linear infinite}
@keyframes spin-slow{to{transform:rotate(360deg)}}
.status{display:flex; gap:12px; align-items:center}
.pill{padding:6px 10px; border-radius:999px; font-size:12px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); color:var(--muted)}
.pill.ok{color:#7cff9a; border-color:rgba(124,255,154,.3); background:rgba(124,255,154,.08)}
.pill.warn{color:#ffb020; border-color:rgba(255,176,32,.3); background:rgba(255,176,32,.08)}
.tab{
  background:rgba(17,17,17,.7); color:var(--muted); border:1px solid rgba(26,26,46,.9); border-bottom:none;
  border-radius:14px 14px 0 0; padding:14px 24px; text-transform:uppercase; font-weight:700; letter-spacing:.5px;
  font-size:16px; transition:all .25s cubic-bezier(.2,.8,.2,1);
}
.tab:hover{color:var(--text); border-color:var(--border); background:rgba(26,26,46,.6); transform:translateY(-2px)}
.tab--selected{background:rgba(26,26,46,.9); border:1px solid var(--border); border-bottom:3px solid var(--accent-cyan); color:var(--accent-cyan); box-shadow:0 -2px 12px rgba(0,242,254,.15) inset}
.dash-tabs{overflow-x:auto}
.dash-tabs .dash-tabs-container{display:flex; justify-content:center; flex-wrap:wrap; gap:8px; background:transparent}
.dash-tabs .dash-tabs .tab{margin:0}
.card{
  background:var(--card); border:1px solid var(--border); border-radius:16px; padding:18px; margin:14px 0;
  backdrop-filter: blur(12px) saturate(140%); box-shadow:0 10px 30px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.03);
  transition:transform .2s ease, box-shadow .2s ease;
}
.card:hover{transform:translateY(-2px); box-shadow:0 14px 40px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04)}
h1,h2,h3{color:var(--text); letter-spacing:.3px}
.accent{color:var(--accent-violet)}
h2.accent, h3.accent{background:linear-gradient(90deg,var(--accent-cyan),var(--accent-violet)); -webkit-background-clip:text; background-clip:text; color:transparent}
a{color:var(--accent-violet)}
.dash-table-container .dash-spreadsheet-container{background:transparent}
/* Sidebar sandwich menu */
.hamburger{font-size:22px;background:var(--bg-elev);border:1px solid var(--border);color:var(--text);border-radius:10px;padding:6px 12px;cursor:pointer;transition:all .2s}
.hamburger:hover{background:var(--cream);border-color:var(--accent-violet)}
.sidebar{position:fixed;top:0;left:0;height:100vh;width:260px;background:linear-gradient(180deg, var(--bg-elev), var(--bg));border-right:1px solid var(--border);backdrop-filter:blur(12px) saturate(140%);z-index:1000;padding-top:70px;transition:transform .32s cubic-bezier(.2,.8,.2,1);overflow-y:auto}
.sidebar.collapsed{transform:translateX(-240px)}
.sidebar-header{padding:12px 18px;font-weight:800;color:var(--text);border-bottom:1px solid var(--border);margin:0 12px 10px 12px}
.sidebar-menu{display:block}
.sidebar-item{display:flex;align-items:center;gap:10px;padding:10px 16px;margin:4px 12px;border-radius:10px;color:var(--muted);cursor:pointer;transition:all .18s}
.sidebar-item:hover{background:var(--cream);color:var(--text)}
.sidebar-item.active{background:var(--cream);color:var(--accent-violet);border:1px solid var(--accent-violet)}
.sidebar-overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:900;display:none}
.sidebar-overlay.visible{display:block}
#main-container{transition:margin-left .32s cubic-bezier(.2,.8,.2,1);margin-left:260px}
.sidebar.collapsed ~ #main-container{margin-left:40px}
@media (max-width:992px){
  #main-container{margin-left:0}
  .sidebar{transform:translateX(-100%)}
  .sidebar:not(.collapsed){transform:translateX(0)}
  .sidebar.collapsed{transform:translateX(-100%)}
  .sidebar-overlay.visible{display:block}
}
/* Custom scrollbars matching white/cream/black palette */
*{scrollbar-width:thin;scrollbar-color:var(--accent-violet) var(--bg-elev);}
::-webkit-scrollbar{width:10px;height:10px;}
::-webkit-scrollbar-track{background:var(--bg-elev);border-radius:8px;}
::-webkit-scrollbar-thumb{background:var(--accent-violet);border-radius:8px;border:2px solid var(--bg-elev);}
::-webkit-scrollbar-thumb:hover{background:var(--accent-cyan);}
#main-container,.sidebar,.card{scrollbar-color:var(--accent-violet) var(--bg-elev);}
#log-pre,.dash-table-container{scrollbar-width:thin;}
/* KPI and gauge cards */
.kpi-card{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:8px;padding:24px !important}
.kpi-card .metric-icon{width:32px;height:32px;opacity:.9}
.kpi-card h4{margin:4px 0;font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600}
.kpi-card .accent{font-size:28px;font-weight:700;margin:0}
.gauge-card{display:flex;flex-direction:column;gap:6px;padding:16px !important}
.gauge-card p{margin:4px 0 0 0;font-weight:600;text-align:center;color:var(--text)}
/* Table enhancements */
.dash-table-container .dash-spreadsheet-container{border-radius:12px;overflow:hidden}
.dash-table-container table{border-collapse:separate;border-spacing:0}
"""

app.index_string = f'''
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}<title>{{%title%}}</title>{{%favicon%}}{{%css%}}
        <style>{dark_css}</style>
    </head>
    <body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body>
</html>'''

auth = dash_auth.BasicAuth(app, VALID_USERS)

tabs_info = [
    {"id": "tab-presentacion", "label": "🏠 PRESENTACIÓN", "title": "PRESENTACIÓN"},
    {"id": "tab-mando", "label": "📡 TELEMETRÍA", "title": "TELEMETRÍA"},
    {"id": "tab-graficas", "label": "📊 GRÁFICAS", "title": "GRÁFICAS"},
    {"id": "tab-fungiverso", "label": "🍄 FUNGIVERSO", "title": "FUNGIVERSO"},
    {"id": "tab-mapas", "label": "🌐 RED UVG", "title": "RED UVG"},
    {"id": "tab-predicciones", "label": "🔮 PREDICCIONES", "title": "PREDICCIONES"},
    {"id": "tab-ml", "label": "🧠 INFERENCIA ML", "title": "INFERENCIA ML"},
    {"id": "tab-asertividad", "label": "🎯 ASERTIVIDAD", "title": "ASERTIVIDAD"},
    {"id": "tab-simulaciones", "label": "⚛️ DEEP PHYSICS & SIMS", "title": "DEEP PHYSICS & SIMS"},
    {"id": "tab-globo", "label": "🌍 GLOBO 3D", "title": "GLOBO 3D"},
    {"id": "tab-espectro", "label": "🌈 ESPECTROGRAMA", "title": "ESPECTROGRAMA"},
    {"id": "tab-corr", "label": "🔗 CORRELACIÓN", "title": "CORRELACIÓN"},
    {"id": "tab-tablas", "label": "💾 DATA LAKE", "title": "DATA LAKE"},
    {"id": "tab-retro", "label": "🔄 RETRO-ANÁLISIS", "title": "RETRO-ANÁLISIS"},
    {"id": "tab-huerfanos", "label": "👻 EVENTOS HUÉRFANOS", "title": "EVENTOS HUÉRFANOS"},
    {"id": "tab-logs", "label": "⚡ LOGS EN VIVO", "title": "LOGS EN VIVO"},
    {"id": "tab-loteria", "label": "🎱 LOTERÍA TÁCTICA", "title": "LOTERÍA TÁCTICA"},
]

def layout_presentacion():
    counters = []
    tables = [
        ("TBL_HISTORICO_SISMICO", "Sismos"),
        ("tbl_clima_espacial_raw", "Clima Espacial"),
        ("tbl_schumann_vivo", "Schumann"),
        ("TBL_DETECCIONES", "Detecciones"),
        ("TBL_CICLOS", "Ciclos"),
    ]
    for tbl, name in tables:
        df = query_df(f"SELECT COUNT(*) as c FROM {tbl}")
        cnt = int(df['c'][0]) if not df.empty else 0
        counters.append(html.Div([
            html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5'><rect x='3' y='3' width='18' height='18' rx='2'/><path d='M7 7h10M7 12h10M7 17h6'/></svg>", className="metric-icon"),
            html.H4(name, style={"margin":"4px 0 2px 0","fontSize":"13px","color":"var(--muted)","textTransform":"uppercase","letterSpacing":".5px"}),
            html.P(str(cnt), className="accent")
        ], className="card kpi-card", style={"display":"inline-block","width":"18%","margin":"1%"}))
    # Model status from TBL_PESOS_BOTS
    pesos = query_df("SELECT bot_name, peso, aciertos, fallos FROM TBL_PESOS_BOTS ORDER BY peso DESC")
    if not pesos.empty:
        # build table
        header = html.Thead(html.Tr([html.Th(col) for col in pesos.columns]))
        body = html.Tbody([html.Tr([html.Td(str(v)) for v in row.values()]) for row in pesos.to_dict('records')])
        model_table = html.Table([header, body], className="card")
        model_card = html.Div([html.H4("Estado Modelo - TBL_PESOS_BOTS"), model_table], className="card")
    else:
        model_card = html.Div([html.H4("Estado Modelo"), html.P("Sin datos", className="card")], className="card")
    # Uptime from TBL_CICLOS
    first_cycle = query_df("SELECT MIN(timestamp) as t0 FROM TBL_CICLOS")
    if not first_cycle.empty and pd.notna(first_cycle['t0'][0]):
        t0 = float(first_cycle['t0'][0])
        now_ts = datetime.now().timestamp()
        uptime_sec = max(0, now_ts - t0)
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        minutes = int((uptime_sec % 3600) // 60)
        uptime_str = f"{days}d {hours}h {minutes}m"
    else:
        uptime_str = "N/A"
    uptime_card = html.Div([
        html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='%230a5a5a' stroke-width='1.5'><circle cx='12' cy='12' r='10'/><polyline points='12 6 12 12 16 14'/></svg>", className="metric-icon"),
        html.H4("Uptime Sistema", style={"margin":"4px 0 2px 0","fontSize":"13px","color":"var(--muted)","textTransform":"uppercase","letterSpacing":".5px"}),
        html.P(uptime_str, className="accent")
    ], className="card kpi-card", style={"display":"inline-block","width":"22%","margin":"1%"})
    # Top 5 sismos recientes as table
    top5 = query_df("SELECT event_id, datetime(timestamp,'unixepoch') as ts, magnitude, lat, lon FROM TBL_HISTORICO_SISMICO ORDER BY timestamp DESC LIMIT 5")
    if not top5.empty:
        header = html.Thead(html.Tr([html.Th(c) for c in top5.columns]))
        body = html.Tbody([html.Tr([html.Td(str(v)) for v in row.values()]) for row in top5.to_dict('records')])
        top_table = html.Table([header, body], className="card")
        top_card = html.Div([html.H4("Top 5 sismos recientes"), top_table], className="card")
    else:
        top_card = html.Div([html.H4("Top 5 sismos recientes"), html.P("Sin datos")], className="card")
    # Mapa sismos M5+ with continent silhouettes
    map_df = query_df("SELECT lat, lon, magnitude FROM TBL_HISTORICO_SISMICO WHERE magnitude >=5.0 ORDER BY timestamp DESC LIMIT 500")
    if not map_df.empty:
        fig = px.scatter_geo(map_df, lat="lat", lon="lon", size="magnitude", color="magnitude", 
                             hover_name="magnitude", projection="natural earth",
                             title="Sismos M5+ - Siluetas continentales")
        fig.update_geos(showcoastlines=True, coastlinecolor="LightGray",
                        showland=True, landcolor="#f7f2e8",
                        showocean=True, oceancolor="#fffdf6",
                        showcountries=True, countrycolor="DimGray")
        fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6",
                          geo=dict(bgcolor="#fffdf6"))
        map_comp = dcc.Graph(figure=fig, className="card", config={"displayModeBar":False})
    else:
        map_comp = html.Div("Sin datos de mapa", className="card")
    return html.Div([html.H2("PRESENTACIÓN", className="accent"),
                     html.Div([
                         html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/></svg>", style={"width":"48px","height":"48px","marginBottom":"10px","display":"block","marginLeft":"auto","marginRight":"auto"}),
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Panel ejecutivo con indicadores de salud del sistema, volúmenes de datos y mapa global de contexto sísmico."),
                         html.Ul([
                             html.Li("Contadores de tablas: Sismos, Clima Espacial, Schumann, Detecciones, Ciclos — volumen acumulado de registros"),
                             html.Li("Uptime Sistema: tiempo de operación desde el primer ciclo registrado"),
                             html.Li("Estado Modelo TBL_PESOS_BOTS: pesos, aciertos y fallos por bot"),
                             html.Li("Top 5 sismos recientes: tabla con los últimos eventos sísmicos"),
                             html.Li("Mapa de contexto global: distribución geográfica de sismos M5+"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     html.Div(counters),
                     html.Div([uptime_card]),
                     model_card,
                     top_card,
                     html.Div([html.H4("Mapa de contexto global")], className="card"),
                     map_comp])

def layout_telemetria():
    clima = query_df("SELECT * FROM tbl_clima_espacial_raw ORDER BY timestamp_blk DESC LIMIT 1")
    sch = query_df("SELECT * FROM tbl_schumann_vivo ORDER BY timestamp_blk DESC LIMIT 1")
    def val(df, col, default=0):
        if df.empty: return default
        return float(df.iloc[0][col]) if col in df.columns and pd.notna(df.iloc[0][col]) else default
    kp = val(clima, "kp_max", 0)
    bz = val(clima, "bz_promedio", 0)
    prot = val(clima, "proton_flux_10mev", 0)
    viento = val(clima, "viento_solar_avg", 0)
    sch_hz = val(sch, "schumann_hz", 0)
    sch_act = val(sch, "schumann_activity", 0)
    gauges = []
    gauge_specs = [
        ("KP Index", kp, 0, 9, "0-3", "3-6", "6-9"),
        ("Bz Component", bz, -30, 30, "-10", "10"),
        ("Flujo de Protones", prot, 0, 1000, "0-300", "300-700", "700-1000"),
        ("Velocidad Viento Solar", viento, 0, 800, "0-400", "400-600", "600-800"),
        ("Frecuencia Schumann", sch_hz, 0, 10, "0-5", "5-8", "8-10"),
        ("Amplitud Schumann", sch_act, 0, 10, "0-3", "3-7", "7-10"),
    ]
    for label, value, gmin, gmax, *steps in gauge_specs:
        # Build gauge steps
        steps_cfg = []
        # simple color steps
        if label == "KP Index":
            steps_cfg = [{"range":[0,3],"color":"#00f2fe"},{"range":[3,6],"color":"#ffb020"},{"range":[6,9],"color":"#ff4d4d"}]
        elif label == "Bz Component":
            steps_cfg = [{"range":[-30,-10],"color":"#1a1a2e"},{"range":[-10,10],"color":"#00f2fe"},{"range":[10,30],"color":"#ff4d4d"}]
        elif label == "Flujo de Protones":
            steps_cfg = [{"range":[0,300],"color":"#00f2fe"},{"range":[300,700],"color":"#ffb020"},{"range":[700,1000],"color":"#ff4d4d"}]
        elif label == "Velocidad Viento Solar":
            steps_cfg = [{"range":[0,400],"color":"#00f2fe"},{"range":[400,600],"color":"#ffb020"},{"range":[600,800],"color":"#ff4d4d"}]
        else:
            steps_cfg = [{"range":[gmin,gmax*0.5],"color":"#00f2fe"},{"range":[gmax*0.5,gmax],"color":"#ffb020"}]
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            domain={'x':[0,1],'y':[0,1]},
            title={'text':label, 'font':{'color':'#e0e0e0'}},
            number={'font':{'color':'#00f2fe'}},
            gauge={
                'axis':{'range':[gmin,gmax],'tickcolor':'#e0e0e0'},
                'bar':{'color':'#00f2fe'},
                'steps':steps_cfg,
                'threshold':{'line':{'color':'white','width':2}}
            }
        ))
        fig.update_layout(template="plotly_white", paper_bgcolor="#fffdf6", plot_bgcolor="#fffdf6", height=250, margin=dict(l=20,r=20,t=40,b=20))
        gauges.append(html.Div([
            dcc.Graph(figure=fig, config={"displayModeBar":False}),
            html.P(label, style={"textAlign":"center","marginTop":"6px","fontWeight":"600","color":"var(--text)"})
        ], className="card gauge-card", style={"display":"inline-block","width":"30%","margin":"1%"}))
    # Host telemetry cards
    try:
        cpu_pct = psutil.cpu_percent(interval=None)
    except Exception:
        cpu_pct = 0
    try:
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
    except Exception:
        ram_pct = 0
    try:
        disk = psutil.disk_usage('/')
        disco_pct = disk.percent
    except Exception:
        disco_pct = 0
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    db_mb = db_size/1024/1024
    def kpi_card(icon, title, value):
        return html.Div([
            html.Img(src=icon, className="metric-icon"),
            html.H4(title, style={"margin":"4px 0 2px 0","fontSize":"13px","color":"var(--muted)","textTransform":"uppercase","letterSpacing":".5px"}),
            html.P(value, className="accent")
        ], className="card kpi-card", style={"display":"inline-block","width":"22%","margin":"1%"})
    cpu_icon = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='%230a5a5a' stroke-width='1.5'><rect x='4' y='4' width='16' height='16' rx='2'/><path d='M9 9h6v6H9z'/></svg>"
    ram_icon = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5'><rect x='3' y='3' width='18' height='18' rx='2'/><path d='M7 7h10M7 12h10M7 17h6'/></svg>"
    disk_icon = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='%238b6a2a' stroke-width='1.5'><rect x='2' y='5' width='20' height='14' rx='2'/><path d='M2 10h20'/></svg>"
    db_icon = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='%237a1a1a' stroke-width='1.5'><ellipse cx='12' cy='5' rx='9' ry='3'/><path d='M3 5v14a9 3 0 0 0 18 0V5'/></svg>"
    host_cards = [
        kpi_card(cpu_icon, "CPU Host", f"{cpu_pct:.1f} %"),
        kpi_card(ram_icon, "RAM Host", f"{ram_pct:.1f} %"),
        kpi_card(disk_icon, "Disco Host", f"{disco_pct:.1f} %"),
        kpi_card(db_icon, "Tamaño DB", f"{db_mb:.1f} MB"),
    ]
    return html.Div([html.H2("TELEMETRÍA", className="accent"),
                     html.Div([
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Monitoreo en tiempo real de indicadores espaciales, Schumann y salud del host."),
                         html.Ul([
                             html.Li("Gráficos de gauge: KP Index, Bz Component, Flujo de Protones, Velocidad Viento Solar, Frecuencia y Amplitud Schumann"),
                             html.Li("Tarjetas Sistema Host: CPU, RAM, Disco y Tamaño de base de datos"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     html.Div([html.H3("Espacio / Schumann", className="accent"), html.Div(gauges)]),
                     html.Div([html.H3("Sistema Host", className="accent"), html.Div(host_cards)])])

def layout_graficas():
    graphs = []
    # KP and Bz time series
    clima = query_df("SELECT timestamp_blk, kp_max, bz_promedio FROM tbl_clima_espacial_raw ORDER BY timestamp_blk DESC LIMIT 2000")
    if not clima.empty:
        clima['timestamp_blk'] = pd.to_datetime(clima['timestamp_blk'], errors='coerce')
        clima = clima.dropna(subset=['timestamp_blk'])
        if not clima.empty:
            ref = clima['timestamp_blk'].max()
            for hrs, title in [(24, 'KP últimas 24h'), (48, 'KP últimas 48h'), (72, 'KP últimas 72h')]:
                dff = clima[clima['timestamp_blk'] >= ref - pd.Timedelta(hours=hrs)]
                if not dff.empty:
                    fig = px.line(dff.sort_values('timestamp_blk'), x='timestamp_blk', y='kp_max', title=title, markers=False)
                    fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6", xaxis_title="Tiempo", yaxis_title="KP")
                    graphs.append(html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False}), className="card"))
            dff_bz = clima[clima['timestamp_blk'] >= ref - pd.Timedelta(hours=24)]
            if not dff_bz.empty:
                fig = px.line(dff_bz.sort_values('timestamp_blk'), x='timestamp_blk', y='bz_promedio', title="Bz últimas 24h")
                fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6", xaxis_title="Tiempo", yaxis_title="Bz nT")
                graphs.append(html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False}), className="card"))
    # Schumann activity
    sch = query_df("SELECT timestamp_blk, schumann_activity FROM tbl_schumann_vivo ORDER BY timestamp_blk DESC LIMIT 2000")
    if not sch.empty:
        sch['timestamp_blk'] = pd.to_datetime(sch['timestamp_blk'], errors='coerce')
        sch = sch.dropna(subset=['timestamp_blk', 'schumann_activity'])
        if not sch.empty:
            ref_s = sch['timestamp_blk'].max()
            dff_s = sch[sch['timestamp_blk'] >= ref_s - pd.Timedelta(hours=24)]
            if not dff_s.empty:
                fig = px.line(dff_s.sort_values('timestamp_blk'), x='timestamp_blk', y='schumann_activity', title="Schumann actividad últimas 24h")
                fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6", xaxis_title="Tiempo", yaxis_title="Actividad")
                graphs.append(html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False}), className="card"))
    # Sismos por día
    sismo = query_df("SELECT timestamp, magnitude FROM TBL_HISTORICO_SISMICO ORDER BY timestamp DESC LIMIT 10000")
    if not sismo.empty:
        sismo['ts_dt'] = pd.to_datetime(sismo['timestamp'], unit='s', errors='coerce')
        sismo = sismo.dropna(subset=['ts_dt'])
        if not sismo.empty:
            ref_sismo = sismo['ts_dt'].max()
            dff_s = sismo[sismo['ts_dt'] >= ref_sismo - pd.Timedelta(days=90)].copy()
            dff_s['date'] = dff_s['ts_dt'].dt.date
            daily = dff_s.groupby('date').size().reset_index(name='count')
            daily['date'] = pd.to_datetime(daily['date'], errors='coerce')
            fig = px.bar(daily, x='date', y='count', title="Sismos por día (últimos 90 días)")
            fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6", xaxis_title="Fecha", yaxis_title="Cantidad")
            graphs.append(html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False}), className="card"))
    # Correlación KP vs Sismos scatter
    kp_daily = query_df("SELECT date(timestamp_blk) as d, AVG(kp_max) as kp_mean FROM tbl_clima_espacial_raw GROUP BY d ORDER BY d DESC LIMIT 365")
    sismo_daily = query_df("SELECT date(datetime(timestamp,'unixepoch')) as d, COUNT(*) as cnt FROM TBL_HISTORICO_SISMICO GROUP BY d ORDER BY d DESC LIMIT 365")
    if not kp_daily.empty and not sismo_daily.empty:
        kp_daily['d'] = pd.to_datetime(kp_daily['d'], errors='coerce')
        sismo_daily['d'] = pd.to_datetime(sismo_daily['d'], errors='coerce')
        merged = pd.merge(kp_daily, sismo_daily, on='d', how='inner')
        if not merged.empty:
            fig = px.scatter(merged, x='kp_mean', y='cnt', hover_data=['d'], title="Correlación KP medio vs Sismos diarios")
            fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6", xaxis_title="KP medio diario", yaxis_title="Sismos/día")
            graphs.append(html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False}), className="card"))
    if not graphs:
        graphs.append(html.Div("Sin datos suficientes para gráficos", className="card"))
    return html.Div([html.H2("GRÁFICAS", className="accent"),
                     html.Div([
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Series temporales, correlaciones y distribuciones de datos espaciales, Schumann y sísmicos."),
                         html.Ul([
                             html.Li("KP últimas 24/48/72h y Bz 24h: líneas temporales de clima espacial"),
                             html.Li("Schumann actividad 24h: línea temporal"),
                             html.Li("Sismos por día 90 días: barras diarias"),
                             html.Li("Correlación KP medio vs sismos diarios: scatter"),
                         ], style={"color":"var(--muted)"})
                     ], className="card")] + graphs)

def layout_fungiverso():
    pc = query_df("SELECT timestamp, fantasma, fase_lunar, schumann_activity, schumann_hz, kp, bz_nT, nivel_riesgo FROM TBL_PRECURSORES_COSMICOS ORDER BY timestamp DESC LIMIT 1")
    if pc.empty:
        return empty_state("FUNGIVERSO")
    row = pc.iloc[0]
    cards = []
    metrics = [
        ("fantasma", row.get('fantasma')),
        ("fase lunar", row.get('fase_lunar')),
        ("schumann activity", row.get('schumann_activity')),
        ("schumann hz", row.get('schumann_hz')),
        ("KP", row.get('kp')),
        ("Bz nT", row.get('bz_nT')),
        ("nivel riesgo", row.get('nivel_riesgo')),
    ]
    for label, val in metrics:
        if pd.notna(val):
            cards.append(html.Div([html.H4(label), html.P(str(val))], className="card", style={"display":"inline-block","width":"22%","margin":"1%"}))
    # Line chart of fantasma over last 200 rows
    hist = query_df("SELECT timestamp, fantasma FROM TBL_PRECURSORES_COSMICOS ORDER BY timestamp DESC LIMIT 200")
    chart_div = html.Div()
    if not hist.empty:
        hist = hist.copy()
        hist['ts'] = pd.to_datetime(hist['timestamp'], unit='s', errors='coerce')
        hist = hist.dropna(subset=['ts','fantasma'])
        hist = hist.sort_values('ts')
        fig = px.line(hist, x='ts', y='fantasma', title="Fantasma últimos registros")
        fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6", xaxis_title="Tiempo", yaxis_title="Fantasma", margin=dict(l=40,r=20,t=40,b=40))
        chart_div = html.Div(dcc.Graph(figure=fig, config={"displayModeBar":False}), className="card")
    return html.Div([html.H2("FUNGIVERSO", className="accent"),
                     html.Div([
                         html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M12 2v8'/><path d='M4.93 10.93a8 8 0 1 1 14.14 0'/><path d='M6 20c0-4.418 3.582-8 8-8s8 3.582 8 8'/></svg>", style={"width":"48px","height":"48px","marginBottom":"10px","display":"block","marginLeft":"auto","marginRight":"auto"}),
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Indicadores cósmicos y métricas del precursor fantasma con evolución temporal."),
                         html.Ul([
                             html.Li("Tarjetas métricas: fantasma, fase lunar, actividad y frecuencia Schumann, KP, Bz, nivel de riesgo"),
                             html.Li("Gráfico línea: evolución del fantasma en últimos registros"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     html.Div(cards), chart_div])

def layout_mapas():
    nodes = query_df("SELECT node_id, nombre, lat, lon, tipo, activo, energia_acumulada, saturacion FROM TBL_NODOS_TOPOLOGIA WHERE lat IS NOT NULL AND lon IS NOT NULL")
    if nodes.empty:
        return empty_state("RED UVG")
    nodes = nodes.copy()
    nodes['estado'] = nodes['activo'].apply(lambda x: 'activo' if x else 'inactivo')
    nodes['peso'] = nodes['energia_acumulada'].fillna(0)
    # Ensure size reasonable
    nodes['peso'] = nodes['peso'].clip(lower=1)
    fig = px.scatter_mapbox(nodes, lat="lat", lon="lon", color="estado", size="peso", hover_name="nombre",
                            hover_data=["node_id","tipo","peso","saturacion"], zoom=1, height=700,
                            size_max=30)
    fig.update_layout(mapbox_style="carto-positron", template="plotly_white", paper_bgcolor="white",
                      plot_bgcolor="#fffdf6", margin=dict(l=0,r=0,t=40,b=0),
                      mapbox=dict(style="carto-positron"),
                      legend=dict(title="Estado del nodo", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return html.Div([html.H2("RED UVG", className="accent"),
                     html.Div([
                         html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z'/><circle cx='12' cy='10' r='3'/></svg>", style={"width":"48px","height":"48px","marginBottom":"10px","display":"block","marginLeft":"auto","marginRight":"auto"}),
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Visualización geográfica de la topología de nodos UVG con estado y energía acumulada."),
                         html.Ul([
                             html.Li("Mapa interactivo Mapbox: nodos con lat/lon, color por estado activo/inactivo y tamaño por energía"),
                             html.Li("Hover con nombre, ID, tipo, peso y saturación"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     dcc.Graph(figure=fig, className="card"),
                     html.Div([html.H5("Leyenda"), html.P("• Color: estado activo/inactivo del nodo • Tamaño: energía acumulada (peso) • Hover muestra ID, tipo, saturación")], className="card", style={"fontSize":"13px","color":"var(--muted)"})])

def layout_predicciones():
    bots_df = query_df("SELECT DISTINCT bot_name FROM TBL_JUEZ_AUDITORIA WHERE resultado='PENDIENTE' AND bot_name IS NOT NULL ORDER BY bot_name")
    bot_options = [{"label": b, "value": b} for b in bots_df['bot_name'].tolist()] if not bots_df.empty else []
    ventanas_df = query_df("SELECT DISTINCT ventana_h FROM TBL_JUEZ_AUDITORIA WHERE resultado='PENDIENTE' AND ventana_h IS NOT NULL ORDER BY ventana_h")
    ventana_options = [{"label": str(int(v)), "value": int(v)} for v in ventanas_df['ventana_h'].tolist()] if not ventanas_df.empty else []
    return html.Div([html.H2("PREDICCIONES", className="accent"),
                     html.Div([
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Consulta y filtrado de predicciones pendientes auditadas por el Juez."),
                         html.Ul([
                             html.Li("Filtros Dropdown: Bot y Ventana h para seleccionar predicciones pendientes"),
                             html.Li("Tabla interactiva predicciones: id, timestamp, bot_name, confianza, ventana_h, resultado"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     html.Div([html.Div("Bot:", style={"marginRight":"10px", "display":"inline-block"}),
                               dcc.Dropdown(id="pred-bot-filter", options=bot_options, multi=True, placeholder="Todos los bots", style={"width":"300px", "display":"inline-block", "backgroundColor":"#ffffff"}),
                               html.Div("Ventana h:", style={"marginLeft":"20px", "marginRight":"10px", "display":"inline-block"}),
                               dcc.Dropdown(id="pred-ventana-filter", options=ventana_options, multi=True, placeholder="Todas", style={"width":"150px", "display":"inline-block", "backgroundColor":"#ffffff"})],
                              className="card"),
                     dash_table.DataTable(id="pred-table",
                                          page_size=20,
                                          page_action="native",
                                          filter_action="native",
                                          sort_action="native",
                                          style_table={"overflowX":"auto","overflowY":"auto","maxHeight":"600px","height":"600px"},
                                          style_header={"backgroundColor":"#f7f2e8", "color":"#111111", "fontWeight":"600", "borderBottom":"1px solid #e8e0d0"},
                                          style_cell={"backgroundColor":"#ffffff", "color":"#111111", "textAlign":"left", "fontFamily":"Inter, Consolas, monospace", "padding":"8px"},
                                          style_cell_hover={"backgroundColor":"#fff8e7"},
                                           style_data_conditional=[{"if":{"row_mod":2},"backgroundColor":"#fffdf6"}])])

def layout_ml():
    sesgo = query_df("SELECT bot, n, recon_insample, recon_causal, sesgo, castigos, n_calma, falsa_alarma, ganancia, consolidadas_sin_exigir, evaluada_at FROM tbl_sesgo_aprendizaje ORDER BY bot")
    pesos = query_df("SELECT bot_name, peso, aciertos, fallos, updated_at FROM TBL_PESOS_BOTS ORDER BY peso DESC")
    
    if not pesos.empty:
        pesos['tasa_acierto'] = pesos.apply(lambda r: r['aciertos']/(r['aciertos']+r['fallos']) if (r['aciertos']+r['fallos'])>0 else None, axis=1)
        total_aciertos = int(pesos['aciertos'].sum())
        total_fallos = int(pesos['fallos'].sum())
        metric_card = html.Div([
            html.H4("Métricas TBL_PESOS_BOTS"),
            html.P(f"Aciertos totales: {total_aciertos}"),
            html.P(f"Fallos totales: {total_fallos}"),
            html.P(f"Bots activos: {len(pesos)}")
        ], className="card")
    else:
        metric_card = html.Div([html.H4("Métricas TBL_PESOS_BOTS"), html.P("Sin datos")], className="card")
    
    def make_table(df, title):
        if df.empty:
            return html.Div([html.H4(title), html.P("Sin datos")], className="card")
        columns = [{"name": str(c), "id": str(c)} for c in df.columns]
        data = df.to_dict("records")
        table = dash_table.DataTable(
            data=data,
            columns=columns,
            page_size=15,
            style_table={"overflowX":"auto","overflowY":"auto","maxHeight":"600px","height":"600px"},
            style_header={"backgroundColor":"#f7f2e8", "color":"#111111", "fontWeight":"600", "borderBottom":"1px solid #e8e0d0"},
            style_cell={"backgroundColor":"#111111","color":"#e0e0e0","fontFamily":"Consolas","textAlign":"left"},
            style_cell_hover={"backgroundColor":"#fff8e7"},
                                           style_data_conditional=[{"if":{"row_mod":2},"backgroundColor":"#fffdf6"}]
        )
        return html.Div([html.H4(title), table], className="card")
    
    return html.Div([
        html.H2("INFERENCIA ML", className="accent"),
        html.Div([
            html.H4("Descripción de la pestaña", className="accent"),
            html.P("Métricas de aprendizaje, sesgo y pesos de bots para inferencia ML."),
            html.Ul([
                html.Li("Métricas TBL_PESOS_BOTS: aciertos totales, fallos totales, bots activos"),
                html.Li("Tabla Sesgo aprendizaje: tbl_sesgo_aprendizaje por bot"),
                html.Li("Tabla Pesos bots: TBL_PESOS_BOTS con tasa de acierto"),
            ], style={"color":"var(--muted)"})
        ], className="card"),
        metric_card,
        make_table(sesgo, "Sesgo aprendizaje (tbl_sesgo_aprendizaje)"),
        make_table(pesos, "Pesos bots (TBL_PESOS_BOTS)")
    ])

def layout_asertividad():
    df = query_df("SELECT bot_name, resultado, COUNT(*) as cnt FROM TBL_JUEZ_AUDITORIA WHERE resultado IN ('ACIERTO','FALLO') GROUP BY bot_name, resultado")
    if df.empty:
        return empty_state("ASERTIVIDAD")
    fig = px.bar(df, x="bot_name", y="cnt", color="resultado", barmode="group", title="Aciertos/Fallos por bot")
    fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6")
    
    pivot = df.pivot(index='bot_name', columns='resultado', values='cnt').fillna(0)
    pivot['total'] = pivot.sum(axis=1)
    pivot['tasa_acierto'] = pivot.apply(lambda r: r.get('ACIERTO',0)/r['total'] if r['total']>0 else None, axis=1)
    pivot = pivot.reset_index()
    columns = [{"name": str(c), "id": str(c)} for c in pivot.columns]
    summary_table = dash_table.DataTable(
        data=pivot.to_dict('records'),
        columns=columns,
        page_size=20,
        style_table={"overflowX":"auto","overflowY":"auto","maxHeight":"600px","height":"600px"},
        style_header={"backgroundColor":"#f7f2e8", "color":"#111111", "fontWeight":"600", "borderBottom":"1px solid #e8e0d0"},
        style_cell={"backgroundColor":"#ffffff", "color":"#111111", "fontFamily":"Inter, Consolas, monospace", "padding":"8px"}
    )
    
    roc_card = html.Div([html.H4("ROC AUC"), html.P("Placeholder: métrica ROC AUC no calculada en DB. Valor pendiente de implementación.")], className="card")
    
    return html.Div([html.H2("ASERTIVIDAD", className="accent"),
                     html.Div([
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Evaluación de aciertos y fallos por bot con métricas de asertividad."),
                         html.Ul([
                             html.Li("Gráfico de barras: aciertos/fallos por bot"),
                             html.Li("Tabla resumen: total y tasa de acierto por bot"),
                             html.Li("Tarjeta ROC AUC: placeholder de métrica"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     dcc.Graph(figure=fig, className="card"),
                     html.Div([html.H4("Resumen por bot"), summary_table], className="card"),
                     roc_card])

def layout_simulaciones():
    tables_df = query_df("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    table_names = tables_df['name'].tolist() if not tables_df.empty else []
    items = [html.Li(name) for name in table_names] if table_names else [html.Li("Sin tablas disponibles")]
    return html.Div([
        html.H2("DEEP PHYSICS & SIMS", className="accent"),
        html.Div([
            html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5'><circle cx='12' cy='12' r='3'/><path d='M12 2v4M12 18v4M2 12h4M18 12h4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83'/></svg>", style={"width":"48px","height":"48px","marginBottom":"10px","display":"block","marginLeft":"auto","marginRight":"auto"}),
            html.H4("Descripción de la pestaña", className="accent"),
            html.P("Zona reservada para simulaciones físicas profundas y exploración de tablas disponibles."),
            html.Ul([
                html.Li("Placeholder informativo sobre ausencia de tablas dedicadas a simulaciones"),
                html.Li("Listado de tablas disponibles en SENTINEL_OMEGA_PRO.db para futuros desarrollos"),
            ], style={"color":"var(--muted)"})
        ], className="card"),
        html.Div([
            html.H4("Placeholder", className="accent"),
            html.P("No existen tablas dedicadas a simulaciones físicas profundas en este momento.", style={"color":"#e0e0e0"}),
            html.P("Tablas disponibles en SENTINEL_OMEGA_PRO.db para futuras simulaciones:", style={"color":"#e0e0e0"}),
            html.Ul(items, style={"color":"#e0e0e0", "paddingLeft":"20px"})
        ], className="card")
    ])

def layout_globo():
    df = query_df("SELECT lat, lon, magnitude, datetime(timestamp,'unixepoch') as ts FROM TBL_HISTORICO_SISMICO WHERE magnitude >=4.5 ORDER BY timestamp DESC LIMIT 2000")
    if df.empty:
        return empty_state("GLOBO 3D")
    fig = px.scatter_geo(df, lat="lat", lon="lon", size="magnitude", color="magnitude", hover_name="magnitude",
                         hover_data=["ts"], projection="natural earth", size_max=25,
                         color_continuous_scale="Reds")
    fig.update_geos(showcoastlines=True, coastlinecolor="#8b6a2a", showland=True, landcolor="#f7f2e8",
                    showocean=True, oceancolor="#fffdf6", showcountries=True, countrycolor="#8b6a2a")
    fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6",
                      margin=dict(l=0,r=0,t=40,b=0), geo_bgcolor="#fffdf6",
                      coloraxis_colorbar=dict(title="Magnitud"))
    return html.Div([html.H2("GLOBO 3D", className="accent"),
                     html.Div([
                         html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/><line x1='2' y1='12' x2='22' y2='12'/><path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/></svg>", style={"width":"48px","height":"48px","marginBottom":"10px","display":"block","marginLeft":"auto","marginRight":"auto"}),
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Mapa geoespacial de eventos sísmicos M4.5+ con proyección global."),
                         html.Ul([
                             html.Li("Scatter geo: lat/lon, tamaño y color por magnitud"),
                             html.Li("Hover con magnitud y timestamp"),
                             html.Li("Proyección Natural Earth con continentes y océanos"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     dcc.Graph(figure=fig, className="card", config={"displayModeBar":False}),
                     html.Div([html.H5("Leyenda"), html.P("Tamaño y color de puntos proporcional a la magnitud del sismo. Escala Reds. Hover muestra timestamp.")], className="card", style={"fontSize":"13px","color":"var(--muted)"})])

def layout_espectro():
    df = query_df("SELECT timestamp_blk, schumann_activity FROM tbl_schumann_vivo ORDER BY timestamp_blk DESC LIMIT 5000")
    if df.empty:
        return empty_state("ESPECTROGRAMA")
    df['timestamp_blk'] = pd.to_datetime(df['timestamp_blk'], errors='coerce')
    df = df.dropna(subset=['timestamp_blk', 'schumann_activity'])
    if df.empty:
        return empty_state("ESPECTROGRAMA")
    df['date'] = df['timestamp_blk'].dt.date
    df['hour'] = df['timestamp_blk'].dt.hour
    pivot = df.pivot_table(index='date', columns='hour', values='schumann_activity', aggfunc='mean')
    pivot = pivot.astype(float)
    if pivot.empty:
        return empty_state("ESPECTROGRAMA")
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[str(h) for h in pivot.columns],
        y=[str(d) for d in pivot.index],
        colorscale='Viridis',
        hoverongaps=False,
        colorbar=dict(title="Actividad")
    ))
    fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6",
                      title="Espectrograma Schumann - Actividad vs Tiempo (aprox. armónica)",
                      xaxis_title="Hora", yaxis_title="Fecha")
    return html.Div([html.H2("ESPECTROGRAMA", className="accent"),
                     html.Div([
                         html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><polyline points='22 12 18 12 15 21 9 3 6 12 2 12'/></svg>", style={"width":"48px","height":"48px","marginBottom":"10px","display":"block","marginLeft":"auto","marginRight":"auto"}),
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Heatmap de actividad Schumann por fecha y hora."),
                         html.Ul([
                             html.Li("Heatmap: eje X hora, eje Y fecha, valor actividad promedio"),
                             html.Li("Escala de color Viridis para intensidad"),
                             html.Li("Aproximación a espectrograma armónico de Schumann"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     dcc.Graph(figure=fig, className="card", config={"displayModeBar": False})])

def layout_corr():
    df = query_df("SELECT event_class, feature, ratio FROM tbl_patrones_correlacion")
    if df.empty:
        return empty_state("CORRELACIÓN")
    # Pivot feature x event_class
    pivot = df.pivot(index="feature", columns="event_class", values="ratio").fillna(0)
    # Ensure numeric
    try:
        pivot = pivot.astype(float)
    except Exception:
        pass
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="RdBu",
        zmid=1.0,
        colorbar=dict(title="Ratio", titleside="right"),
        hoverongaps=False,
        hovertemplate="Feature: %{y}<br>Event Class: %{x}<br>Ratio: %{z:.3f}<extra></extra>"
    ))
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="#fffdf6",
        title=dict(text="Heatmap correlación: feature x event_class", font=dict(color="#e0e0e0")),
        xaxis=dict(title="Event Class", tickangle=-30, title_font=dict(color="#e0e0e0"), tickfont=dict(color="#e0e0e0")),
        yaxis=dict(title="Feature", title_font=dict(color="#e0e0e0"), tickfont=dict(color="#e0e0e0")),
        margin=dict(l=100, r=40, t=60, b=100)
    )
    return html.Div([html.H2("CORRELACIÓN", className="accent"),
                     html.Div([
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Heatmap de correlación entre features y clases de evento desde tbl_patrones_correlacion."),
                         html.Ul([
                             html.Li("Heatmap: ratio feature x event_class con escala RdBu centrada en 1.0"),
                             html.Li("Tabla pivoteada a partir de tbl_patrones_correlacion"),
                             html.Li("Hover con valores de ratio detallados"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     html.Div([html.P("tbl_patrones_correlacion — pivot feature x event_class con ratio", className="accent")], className="card"),
                     dcc.Graph(figure=fig, className="card", config={"displayModeBar": False})])

DATA_LAKE_TABLES = [
    {"label": "TBL_CICLOS", "value": "TBL_CICLOS"},
    {"label": "TBL_HISTORICO_SISMICO", "value": "TBL_HISTORICO_SISMICO"},
    {"label": "tbl_clima_espacial_raw", "value": "tbl_clima_espacial_raw"},
    {"label": "tbl_schumann_vivo", "value": "tbl_schumann_vivo"},
]

def layout_tablas():
    return html.Div([html.H2("DATA LAKE", className="accent"),
                     html.Div([
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Explorador interactivo de tablas principales del data lake con descarga CSV."),
                         html.Ul([
                             html.Li("Selector de tabla: TBL_CICLOS, TBL_HISTORICO_SISMICO, tbl_clima_espacial_raw, tbl_schumann_vivo"),
                             html.Li("Tabla paginada con últimos 100 registros"),
                             html.Li("Botón Descargar CSV para exportar vista actual"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     html.Div([html.Div("Tabla:", style={"marginRight": "10px", "display":"inline-block"}),
                               dcc.Dropdown(id="data-lake-table-selector",
                                            options=DATA_LAKE_TABLES,
                                            value="TBL_CICLOS",
                                            clearable=False,
                                            style={"width": "300px", "display":"inline-block", "backgroundColor":"#ffffff"})],
                              className="card"),
                     html.Div([html.Button("Descargar CSV", id="data-lake-download-btn", className="accent", style={"marginBottom":"10px", "backgroundColor":"#ffffff", "border":"1px solid #00f2fe", "color":"#00f2fe", "padding":"6px 12px", "borderRadius":"6px", "cursor":"pointer"}),
                               dash_table.DataTable(id="data-lake-table",
                                                    page_size=20,
                                                    page_action="native",
                                                    style_table={"overflowX":"auto","overflowY":"auto","maxHeight":"600px","height":"600px"},
                                                    style_header={"backgroundColor":"#f7f2e8", "color":"#111111", "fontWeight":"600", "borderBottom":"1px solid #e8e0d0"},
                                                    style_cell={"backgroundColor":"#ffffff", "color":"#111111", "textAlign":"left", "fontFamily":"Inter, Consolas, monospace", "padding":"8px"},
                                                    style_cell_hover={"backgroundColor":"#fff8e7"},
                                           style_data_conditional=[{"if":{"row_mod":2},"backgroundColor":"#fffdf6"}])],
                              className="card"),
                     dcc.Download(id="data-lake-download")])

def layout_retro():
    df = query_df("SELECT id, timestamp, bot_name, resultado, confianza, ventana_h FROM TBL_JUEZ_AUDITORIA WHERE resultado != 'PENDIENTE' ORDER BY timestamp DESC LIMIT 500")
    if df.empty:
        return empty_state("RETRO-ANÁLISIS")
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
        df = df.dropna(subset=['timestamp_dt'])
    fig = px.scatter(df, x="timestamp_dt", y="confianza", color="resultado", hover_data=["bot_name","ventana_h"], title="Confianza vs Tiempo (predicciones resueltas)")
    fig.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="#fffdf6", xaxis_title="Fecha", yaxis_title="Confianza")
    return html.Div([html.H2("RETRO-ANÁLISIS", className="accent"),
                     html.Div([
                         html.H4("Descripción de la pestaña", className="accent"),
                         html.P("Análisis retrospectivo de predicciones resueltas por el Juez."),
                         html.Ul([
                             html.Li("Scatter confianza vs tiempo para predicciones resueltas"),
                             html.Li("Color por resultado: ACIERTO/FALLO"),
                             html.Li("Hover con bot_name y ventana_h"),
                         ], style={"color":"var(--muted)"})
                     ], className="card"),
                     dcc.Graph(figure=fig, className="card")])

def layout_huerfanos():
    df = query_df("""
        SELECT magnitude, datetime(timestamp,'unixepoch') as timestamp, region
        FROM TBL_HISTORICO_SISMICO
        WHERE event_id NOT IN (SELECT CAST(event_id AS TEXT) FROM tbl_eventos_catalogo)
        ORDER BY timestamp DESC
        LIMIT 500
    """)
    if df.empty:
        return html.Div([html.H2("EVENTOS HUÉRFANOS", className="accent"), html.Div("Sin eventos huérfanos encontrados o tabla vacía.", className="card")])
    columns = [{"name": str(c).capitalize(), "id": str(c)} for c in df.columns]
    data = df.to_dict("records")
    table = dash_table.DataTable(
        data=data,
        columns=columns,
        page_size=20,
        page_action="native",
        style_table={"overflowX":"auto","overflowY":"auto","maxHeight":"600px","height":"600px"},
        style_header={"backgroundColor":"#f7f2e8", "color":"#111111", "fontWeight":"600", "borderBottom":"1px solid #e8e0d0"},
        style_cell={"backgroundColor":"#ffffff", "color":"#111111", "textAlign":"left", "fontFamily":"Inter, Consolas, monospace", "padding":"8px"},
        style_cell_hover={"backgroundColor":"#fff8e7"},
                                           style_data_conditional=[{"if":{"row_mod":2},"backgroundColor":"#fffdf6"}]
    )
    return html.Div([
        html.H2("EVENTOS HUÉRFANOS", className="accent"),
        html.Div([
            html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5'><path d='M9 2h6v6l2 2v8a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-8l2-2V2z'/><circle cx='12' cy='13' r='3'/></svg>", style={"width":"48px","height":"48px","marginBottom":"10px","display":"block","marginLeft":"auto","marginRight":"auto"}),
            html.H4("Descripción de la pestaña", className="accent"),
            html.P("Listado de eventos sísmicos sin correspondencia en catálogo oficial."),
            html.Ul([
                html.Li("Tabla paginada de eventos huérfanos: magnitud, timestamp, región"),
                html.Li("Consulta SQL contra TBL_HISTORICO_SISMICO excluyendo tbl_eventos_catalogo"),
            ], style={"color":"var(--muted)"})
        ], className="card"),
        html.Div([
            html.H4("Eventos sísmicos sin catálogo asociado"),
            html.P("Consulta: TBL_HISTORICO_SISMICO WHERE event_id NOT IN (SELECT event_id FROM tbl_eventos_catalogo)", style={"color":"#aaa"}),
            table
        ], className="card")
    ])

def layout_logs():
    log_path = BASE_DIR / "logs" / "sentinel_omega.log"
    level_options = [
        {"label": "Todos", "value": "ALL"},
        {"label": "INFO", "value": "INFO"},
        {"label": "DEBUG", "value": "DEBUG"},
        {"label": "WARNING", "value": "WARNING"},
        {"label": "ERROR", "value": "ERROR"},
        {"label": "CRITICAL", "value": "CRITICAL"},
    ]
    return html.Div([
        html.H2("LOGS EN VIVO", className="accent"),
        html.Div([
            html.H4("Descripción de la pestaña", className="accent"),
            html.P("Visor en vivo del archivo de logs con filtro por nivel."),
            html.Ul([
                html.Li("Filtro Dropdown por nivel: ALL, INFO, DEBUG, WARNING, ERROR, CRITICAL"),
                html.Li("Auto-refresh cada 10s con Interval"),
                html.Li("Pre-formateado de últimas 200 líneas del log"),
            ], style={"color":"var(--muted)"})
        ], className="card"),
        html.Div([
            html.Div("Nivel:", style={"marginRight":"10px","display":"inline-block","color":"#e0e0e0"}),
            dcc.Dropdown(id="log-level-filter", options=level_options, value="ALL", clearable=False,
                         style={"width":"200px","display":"inline-block","backgroundColor":"#ffffff"}),
            html.Div(style={"width":"20px","display":"inline-block"}),
        ], className="card"),
        dcc.Interval(id="log-interval", interval=10000, n_intervals=0),
        html.Pre(id="log-pre", className="card", style={"whiteSpace":"pre-wrap","maxHeight":"600px","overflowY":"auto","backgroundColor":"#111111","padding":"12px"})
    ])

def layout_loteria():
    return html.Div([
        html.H2("LOTERÍA TÁCTICA", className="accent"),
        html.Div([
            html.Img(src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%234a3a7a' stroke-width='1.5'><rect x='4' y='4' width='16' height='16' rx='2'/><path d='M10 10h4v4h-4z'/><circle cx='8' cy='8' r='1'/><circle cx='16' cy='16' r='1'/></svg>", style={"width":"48px","height":"48px","marginBottom":"10px","display":"block","marginLeft":"auto","marginRight":"auto"}),
            html.H4("Descripción de la pestaña", className="accent"),
            html.P("Información sobre integración externa con datos de lotería táctica TITAN."),
            html.Ul([
                html.Li("Datos externos: no residen en SENTINEL_OMEGA_PRO.db"),
                html.Li("Origen: TITAN_MEMORY.db externo, sin generación sintética"),
                html.Li("Política de integridad: cero datos fabricados"),
            ], style={"color":"var(--muted)"})
        ], className="card"),
        html.Div([
            html.H4("Datos externos - TITAN"),
            html.P("Los datos de lotería táctica no residen en SENTINEL_OMEGA_PRO.db.", style={"color":"#e0e0e0"}),
            html.P("Origen: TITAN_MEMORY.db externo a Sentinel Omega. No se genera datos sintéticos.", style={"color":"#e0e0e0"}),
            html.P("Nota:", className="accent"),
            html.Ul([
                html.Li("No se crean registros sintéticos de lotería en este dashboard."),
                html.Li("Toda información táctica proviene de TITAN_MEMORY.db mediante integración externa."),
                html.Li("Consulta externa requerida para análisis de predicción."),
                html.Li("Política de integridad: cero datos fabricados.")
            ], style={"color":"#e0e0e0", "paddingLeft":"20px"})
        ], className="card")
    ])

tab_builders = {
    "tab-presentacion": layout_presentacion,
    "tab-mando": layout_telemetria,
    "tab-graficas": layout_graficas,
    "tab-fungiverso": layout_fungiverso,
    "tab-mapas": layout_mapas,
    "tab-predicciones": layout_predicciones,
    "tab-ml": layout_ml,
    "tab-asertividad": layout_asertividad,
    "tab-simulaciones": layout_simulaciones,
    "tab-globo": layout_globo,
    "tab-espectro": layout_espectro,
    "tab-corr": layout_corr,
    "tab-tablas": layout_tablas,
    "tab-retro": layout_retro,
    "tab-huerfanos": layout_huerfanos,
    "tab-logs": layout_logs,
    "tab-loteria": layout_loteria,
}

app.layout = html.Div(id="app-root", children=[
    dcc.Store(id='sidebar-collapsed-store', storage_type='local', data=False),
    html.Div(className="cymatic-grid"),
    dcc.Location(id="url", refresh=False),
    html.Div(id='sidebar', className='sidebar', children=[
        html.Div(className='sidebar-header', children=[html.Span('Sentinel Omega')]),
        html.Div(className='sidebar-menu', children=[
            html.Button(
                t["label"],
                id={'type':'sidebar-tab-btn','index':t["id"]},
                n_clicks=0,
                className='sidebar-item',
                style={'width':'100%','textAlign':'left'}
            )
            for t in tabs_info
        ])
    ]),
    html.Button('', id='sidebar-overlay', className='sidebar-overlay', n_clicks=0),
    html.Div(id="main-container", children=[
        html.Div(className="header", children=[
            html.Button('☰', id='sidebar-toggle', className='hamburger', n_clicks=0),
            html.Div(className="logo", children=[
                html.Div(className="logo-mark"),
                html.Span("Sentinel Omega", style={"fontSize":"20px"})
            ]),
            html.Div(className="status", children=[
                html.Span("DB OK", className="pill ok"),
                html.Span("API ACTIVA", className="pill ok"),
                html.Span("Modo Oscuro", className="pill warn")
            ])
        ]),
        dcc.Tabs(id="tabs", value=tabs_info[0]["id"], style={'display':'none'}, children=[
            dcc.Tab(label=t["label"], value=t["id"], className="tab", selected_className="tab--selected")
            for t in tabs_info
        ]),
        html.Div(id="tab-content", style={"marginTop": "20px"})
    ])
])

@app.callback(
    dash.dependencies.Output("tab-content", "children"),
    dash.dependencies.Input("tabs", "value")
)
def render_tab(tab_id):
    builder = tab_builders.get(tab_id)
    if builder:
        try:
            return builder()
        except Exception as e:
            return html.Div([html.H2(tab_id, className="accent"), html.Div(f"Error: {e}", className="card")])
    return empty_state()


@app.callback(
    dash.dependencies.Output('tabs', 'value'),
    dash.dependencies.Input({'type':'sidebar-tab-btn','index':dash.dependencies.ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def sync_sidebar_buttons(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
    # btn_id is like {'type':'sidebar-tab-btn','index':'tab-presentacion'}
    import json
    try:
        btn = json.loads(btn_id)
        return btn.get('index')
    except Exception:
        return dash.exceptions.PreventUpdate



@app.callback(
    dash.dependencies.Output('sidebar-collapsed-store', 'data'),
    dash.dependencies.Input('sidebar-toggle', 'n_clicks'),
    dash.dependencies.State('sidebar-collapsed-store', 'data'),
    prevent_initial_call=True
)
def toggle_sidebar(n_clicks, collapsed):
    if n_clicks is None:
        return collapsed
    return not collapsed


@app.callback(
    dash.dependencies.Output('sidebar-collapsed-store', 'data'),
    dash.dependencies.Input('sidebar-overlay', 'n_clicks'),
    dash.dependencies.State('sidebar-collapsed-store', 'data'),
    prevent_initial_call=True
)
def close_sidebar_on_overlay(n_clicks, collapsed):
    # Close sidebar when overlay is clicked (mobile)
    if n_clicks:
        return True
    return collapsed


@app.callback(
    dash.dependencies.Output('sidebar', 'className'),
    dash.dependencies.Output('sidebar-overlay', 'className'),
    dash.dependencies.Input('sidebar-collapsed-store', 'data')
)
def update_sidebar_class(collapsed):
    sidebar_cls = 'sidebar collapsed' if collapsed else 'sidebar'
    overlay_cls = 'sidebar-overlay' if collapsed else 'sidebar-overlay visible'
    return sidebar_cls, overlay_cls


# --- Callbacks for interactive tabs ---

@app.callback(
    [dash.dependencies.Output("data-lake-table", "data"),
     dash.dependencies.Output("data-lake-table", "columns")],
    dash.dependencies.Input("data-lake-table-selector", "value")
)
def update_data_lake_table(table_name):
    if not table_name:
        return [], []
    # Validate table name against whitelist
    allowed = {t["value"] for t in DATA_LAKE_TABLES}
    if table_name not in allowed:
        return [], []
    sql = f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 100"
    df = query_df(sql)
    if df.empty:
        return [], []
    # Rename columns to strings
    columns = [{"name": str(c), "id": str(c)} for c in df.columns]
    data = df.to_dict("records")
    return data, columns


@app.callback(
    dash.dependencies.Output("data-lake-download", "data"),
    dash.dependencies.Input("data-lake-download-btn", "n_clicks"),
    dash.dependencies.State("data-lake-table-selector", "value"),
    prevent_initial_call=True
)
def download_data_lake_csv(n_clicks, table_name):
    if not n_clicks or not table_name:
        return None
    allowed = {t["value"] for t in DATA_LAKE_TABLES}
    if table_name not in allowed:
        return None
    sql = f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 100"
    df = query_df(sql)
    if df.empty:
        return None
    # Return CSV
    return dict(content=df.to_csv(index=False), filename=f"{table_name}_last100.csv")


@app.callback(
    [dash.dependencies.Output("pred-table", "data"),
     dash.dependencies.Output("pred-table", "columns")],
    [dash.dependencies.Input("pred-bot-filter", "value"),
     dash.dependencies.Input("pred-ventana-filter", "value")]
)
def update_pred_table(bot_filter, ventana_filter):
    base_sql = "SELECT id, timestamp, bot_name, confianza, ventana_h, resultado FROM TBL_JUEZ_AUDITORIA WHERE resultado='PENDIENTE'"
    params = []
    conditions = []
    if bot_filter:
        # bot_filter is list
        placeholders = ",".join(["?"] * len(bot_filter))
        conditions.append(f"bot_name IN ({placeholders})")
        params.extend(bot_filter)
    if ventana_filter:
        placeholders = ",".join(["?"] * len(ventana_filter))
        conditions.append(f"ventana_h IN ({placeholders})")
        params.extend(ventana_filter)
    if conditions:
        base_sql += " AND " + " AND ".join(conditions)
    base_sql += " ORDER BY timestamp DESC LIMIT 500"
    df = query_df(base_sql, tuple(params))
    if df.empty:
        return [], []
    columns = [{"name": str(c), "id": str(c)} for c in df.columns]
    data = df.to_dict("records")
    return data, columns


@app.callback(
    dash.dependencies.Output("log-pre", "children"),
    dash.dependencies.Input("log-interval", "n_intervals"),
    dash.dependencies.State("log-level-filter", "value")
)
def update_log_tail(n_intervals, level):
    log_path = BASE_DIR / "logs" / "sentinel_omega.log"
    lines = []
    try:
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                # tail last 200 lines
                tail = all_lines[-200:] if len(all_lines) > 200 else all_lines
                if level and level != "ALL":
                    tail = [l for l in tail if level in l]
                lines = "".join(tail)
        else:
            lines = "Log no disponible"
    except Exception as e:
        lines = f"Error leyendo log: {e}"
    return lines


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8128, debug=False)
