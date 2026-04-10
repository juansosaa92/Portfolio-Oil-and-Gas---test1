# ============================================================
# Dashboard CHA.Nq.ET-2043(h) — Producción + Trayectoria 3D
# Formación Vaca Muerta · El Trapial Este · Chevron Argentina
#
# Para correr:
#   pip install streamlit plotly pandas numpy
#   streamlit run dashboard_produccion.py
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Configuración de página ──────────────────────────────────
st.set_page_config(
    page_title="ET-2043(h) · Vaca Muerta",
    page_icon="🛢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Helpers ──────────────────────────────────────────────────
def hex_to_rgba(hex_color, opacity=0.15):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{opacity})"

def make_colorscale(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return [
        [0,   f"rgba({int(r*0.5)},{int(g*0.5)},{int(b*0.5)},0.72)"],
        [0.5, f"rgba({int(r*0.75)},{int(g*0.75)},{int(b*0.75)},0.72)"],
        [1,   f"rgba({r},{g},{b},0.72)"]
    ]

# ── Estilos custom ───────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .stMetric label { font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Constantes de color ───────────────────────────────────────
POZO_COLOR  = "#58a6ff"
AGUA_COLOR  = "#4fc3f7"
GAS_COLOR   = "#3fb950"
NOMBRE_POZO = "CHA.Nq.ET-2043(h)"

# ── Columna estratigráfica (profundidades ajustadas a 5.868 m) ──
STRAT = [
    {"name": "Neuquén",     "top": 0,    "base": 1200, "color": "#8b6f4e", "texture": "granular"},
    {"name": "Rayoso",      "top": 1200, "base": 1800, "color": "#4a9eff", "texture": "laminar"},
    {"name": "Agrio",       "top": 1800, "base": 2500, "color": "#a0c4ff", "texture": "nodular"},
    {"name": "Quintuco",    "top": 2500, "base": 3400, "color": "#ffd700", "texture": "masivo"},
    {"name": "VM Superior", "top": 3400, "base": 4200, "color": "#3fb950", "texture": "ondulado"},
    {"name": "VM Inferior", "top": 4200, "base": 5000, "color": "#f78166", "texture": "laminado"},
    {"name": "Tordillo",    "top": 5000, "base": 5500, "color": "#d2a8ff", "texture": "cruzado"},
    {"name": "Precuyano",   "top": 5500, "base": 5868, "color": "#ff6b6b", "texture": "irregular"},
]

# ── Carga y procesamiento de datos reales ─────────────────────
@st.cache_data
def cargar_datos(ruta="pozo1_data.csv"):
    df = pd.read_csv(ruta)

    # Filtrar meses con producción cero (pre-producción)
    df = df[(df["prod_pet"] > 0) | (df["prod_gas"] > 0)].copy()

    # Construir fecha y ordenar
    df["fecha"] = pd.to_datetime(
        df["anio"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2) + "-01"
    )
    df = df.sort_values("fecha").reset_index(drop=True)

    # Días por mes para convertir m³/mes → m³/día
    df["dias"] = df["fecha"].dt.days_in_month

    # Tasas diarias
    df["oil_m3d"]  = (df["prod_pet"]  / df["dias"]).round(1)
    df["gas_mm3d"] = (df["prod_gas"]  / df["dias"] / 1000).round(4)   # Mm³/d
    df["agua_m3d"] = (df["prod_agua"] / df["dias"]).round(1)

    # GOR (m³/m³) — gas en m³, petróleo en m³
    df["gor"] = (df["prod_gas"] / df["prod_pet"]).round(1)

    # Corte de agua WC (%)
    liquido = df["prod_pet"] + df["prod_agua"]
    df["wc"] = (df["prod_agua"] / liquido * 100).round(1)

    # Producción acumulada (m³)
    df["cum_oil"]  = df["prod_pet"].cumsum().round(0).astype(int)
    df["cum_agua"] = df["prod_agua"].cumsum().round(0).astype(int)

    return df

df_full = cargar_datos()

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Parámetros")
    st.markdown("---")

    n_meses = len(df_full)
    periodo = st.slider("Período (meses):", 6, n_meses, n_meses, 1)
    escala_y = st.radio("Escala eje Y:", ["Lineal", "Logarítmica"])

    st.markdown("---")
    st.markdown(f"**📍 {NOMBRE_POZO}**")
    st.markdown("El Trapial Este · Neuquén")
    st.markdown("Formación Vaca Muerta")
    st.markdown("**Chevron Argentina S.R.L.**")
    st.markdown("---")
    st.markdown("**🔧 Datos del pozo**")
    st.caption("Tipo: Petrolífero horizontal")
    st.caption("Extracción: Surgencia natural")
    st.caption("Profundidad: 5.868 m")
    st.caption("Área: El Trapial Este")
    st.caption("ID Pozo: 164531")
    inicio = df_full["fecha"].min().strftime("%b %Y")
    fin    = df_full["fecha"].max().strftime("%b %Y")
    st.caption(f"Período: {inicio} – {fin}")

# ── Filtrar por período ───────────────────────────────────────
df = df_full.head(periodo).copy()

# ── Trayectoria 3D ────────────────────────────────────────────
@st.cache_data
def generar_trayectoria():
    dip_rate = np.tan(2 * np.pi / 180)
    az       = 85 * np.pi / 180
    kickoff  = 1500
    tvd_tgt  = 5100
    horz_len = 2500

    xs, ys, zs = [], [], []

    # Sección vertical hasta KOP
    for i in range(41):
        xs.append(0.0); ys.append(0.0); zs.append(-(kickoff / 40) * i)

    # Build-up
    build_len = (tvd_tgt - kickoff) * 1.62
    tvd_c, e_c, n_c = kickoff, 0.0, 0.0
    for i in range(1, 81):
        inc   = (i / 80) * np.pi / 2
        dl    = build_len / 80
        tvd_c = min(tvd_c + dl * np.cos(inc), tvd_tgt)
        e_c  += dl * np.sin(inc) * np.sin(az)
        n_c  += dl * np.sin(inc) * np.cos(az)
        xs.append(e_c); ys.append(n_c); zs.append(-tvd_c)

    # Rama horizontal
    lx, ly, lz = xs[-1], ys[-1], zs[-1]
    for i in range(1, 81):
        d = (horz_len / 80) * i
        xs.append(lx + d * np.sin(az))
        ys.append(ly + d * np.cos(az))
        zs.append(lz - d * np.sin(az) * dip_rate)

    return xs, ys, zs

traj = generar_trayectoria()

# ── Superficies estratigráficas ───────────────────────────────
@st.cache_data
def generar_superficies():
    xs_t, ys_t, _ = generar_trayectoria()
    NX, NY = 25, 18
    xg = np.linspace(-300, max(xs_t) + 300, NX)
    yg = np.linspace(-300, max(abs(y) for y in ys_t) + 300, NY)
    dip = np.tan(2 * np.pi / 180)
    surfaces = []
    for s in STRAT:
        Z = np.array([[-(s["top"] + x * dip) for x in xg] for _ in yg])
        C = np.zeros((NY, NX))
        t = s["texture"]
        for j, y in enumerate(yg):
            for i, x in enumerate(xg):
                if t == "granular":
                    C[j,i] = np.sin(x*0.08)*np.cos(y*0.08) + np.sin(x*0.19+1.3)*0.5
                elif t == "laminar":
                    C[j,i] = np.sin(y*0.35) + np.sin(y*0.7)*0.3
                elif t == "nodular":
                    C[j,i] = np.sin(x*0.05)*np.sin(y*0.08) + np.cos(x*0.12)*0.4
                elif t == "masivo":
                    C[j,i] = (x / (max(xs_t) + 600)) * 0.3 + np.sin(x*0.01+y*0.01)*0.1
                elif t == "ondulado":
                    C[j,i] = np.sin(x*0.025+y*0.015) + np.cos(x*0.012)*0.5
                elif t == "laminado":
                    C[j,i] = np.sin(y*0.5) + np.sin(y*1.1)*0.4 + np.sin(x*0.03)*0.2
                elif t == "cruzado":
                    C[j,i] = np.sin((x+y)*0.06) + np.sin((x-y)*0.04)*0.6
                else:
                    C[j,i] = np.sin(x*0.1)*np.cos(y*0.13) + np.sin(x*0.07+y*0.09)*0.7
        surfaces.append({
            "name": s["name"], "color": s["color"],
            "top": s["top"],   "base": s["base"],
            "xg": xg.tolist(), "yg": yg.tolist(),
            "Z": Z.tolist(),   "C": C.tolist(),
            "is_target": s["name"] == "VM Inferior"
        })
    return surfaces

surfaces = generar_superficies()

# ════════════════════════════════════════════════════════════
# LAYOUT PRINCIPAL
# ════════════════════════════════════════════════════════════
st.title("🛢 CHA.Nq.ET-2043(h) — Dashboard Vaca Muerta")
st.markdown("**Formación Vaca Muerta · El Trapial Este · Chevron Argentina S.R.L. · Datos reales (Capítulo IV)**")
st.markdown("---")

tab1, tab2 = st.tabs(["📊 Producción", "🌍 Trayectoria 3D"])

# ════════════════════════════════════════════════════════════
# TAB 1: PRODUCCIÓN
# ════════════════════════════════════════════════════════════
with tab1:

    # ── KPIs ─────────────────────────────────────────────────
    st.subheader("Indicadores del Pozo")

    pico_oil   = df["oil_m3d"].max()
    actual_oil = df["oil_m3d"].iloc[-1]
    cum_oil    = df["cum_oil"].iloc[-1]
    cum_agua   = df["cum_agua"].iloc[-1]
    delta_oil  = round((actual_oil - pico_oil) / pico_oil * 100, 1)
    pico_gor   = df["gor"].max()
    actual_gor = df["gor"].iloc[-1]
    wc_actual  = df["wc"].iloc[-1]
    avg_gas    = df["gas_mm3d"].mean()

    col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
    with col_k1:
        st.metric("🛢 Petróleo actual", f"{actual_oil:,.0f} m³/d",
                  delta=f"{delta_oil}% vs pico")
        st.caption(f"Pico: {pico_oil:,.0f} m³/d")
    with col_k2:
        st.metric("📦 Acum. petróleo", f"{cum_oil/1000:,.1f} km³")
        st.caption(f"{cum_oil:,.0f} m³ totales")
    with col_k3:
        st.metric("💧 Corte de agua", f"{wc_actual:.1f} %")
        st.caption(f"Acum. agua: {cum_agua/1000:,.1f} km³")
    with col_k4:
        st.metric("⚗️ GOR actual", f"{actual_gor:,.0f} m³/m³")
        st.caption(f"GOR pico: {pico_gor:,.0f} m³/m³")
    with col_k5:
        st.metric("💨 Gas promedio", f"{avg_gas:.3f} Mm³/d")
        st.caption("Surgencia natural")

    st.markdown("---")

    # ── Petróleo + Gas ────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🛢 Petróleo (m³/d)")
        fig_oil = go.Figure()
        fig_oil.add_trace(go.Scatter(
            x=df["fecha"], y=df["oil_m3d"],
            name="Petróleo",
            mode="lines+markers",
            fill="tozeroy",
            fillcolor=hex_to_rgba(POZO_COLOR, 0.12),
            line=dict(color=POZO_COLOR, width=2.5),
            marker=dict(size=5, color=POZO_COLOR),
            hovertemplate="<b>%{x|%b %Y}</b><br>%{y:.1f} m³/d<extra></extra>"
        ))
        fig_oil.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_type="log" if escala_y == "Logarítmica" else "linear",
            yaxis_title="m³/d", height=300,
            margin=dict(t=10, b=40, l=55, r=10), hovermode="x unified"
        )
        st.plotly_chart(fig_oil, use_container_width=True)

    with col2:
        st.subheader("💨 Gas (Mm³/d)")
        fig_gas = go.Figure()
        fig_gas.add_trace(go.Scatter(
            x=df["fecha"], y=df["gas_mm3d"],
            name="Gas",
            mode="lines+markers",
            fill="tozeroy",
            fillcolor=hex_to_rgba(GAS_COLOR, 0.12),
            line=dict(color=GAS_COLOR, width=2.5),
            marker=dict(size=5, color=GAS_COLOR),
            hovertemplate="<b>%{x|%b %Y}</b><br>%{y:.4f} Mm³/d<extra></extra>"
        ))
        fig_gas.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_title="Mm³/d", height=300,
            margin=dict(t=10, b=40, l=55, r=10), hovermode="x unified"
        )
        st.plotly_chart(fig_gas, use_container_width=True)

    # ── Acumulada + GOR/WC ────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📈 Producción Acumulada (m³)")
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=df["fecha"], y=df["cum_oil"],
            name="Petróleo acum.",
            mode="lines",
            fill="tozeroy",
            fillcolor=hex_to_rgba(POZO_COLOR, 0.15),
            line=dict(color=POZO_COLOR, width=2),
            hovertemplate="<b>%{x|%b %Y}</b><br>Petróleo: %{y:,.0f} m³<extra></extra>"
        ))
        fig_cum.add_trace(go.Scatter(
            x=df["fecha"], y=df["cum_agua"],
            name="Agua acum.",
            mode="lines",
            fill="tozeroy",
            fillcolor=hex_to_rgba(AGUA_COLOR, 0.10),
            line=dict(color=AGUA_COLOR, width=2, dash="dot"),
            hovertemplate="<b>%{x|%b %Y}</b><br>Agua: %{y:,.0f} m³<extra></extra>"
        ))
        fig_cum.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", yaxis_title="m³ acumulados", height=300,
            margin=dict(t=10, b=40, l=65, r=10), hovermode="x unified"
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    with col4:
        st.subheader("⚗️ GOR y Corte de Agua")
        fig_gor = make_subplots(specs=[[{"secondary_y": True}]])
        fig_gor.add_trace(go.Scatter(
            x=df["fecha"], y=df["gor"],
            name="GOR", mode="lines+markers",
            line=dict(color=GAS_COLOR, width=2),
            marker=dict(size=4),
            hovertemplate="GOR: %{y:.0f} m³/m³<extra></extra>"
        ), secondary_y=False)
        fig_gor.add_trace(go.Scatter(
            x=df["fecha"], y=df["wc"],
            name="Corte agua (WC)", mode="lines+markers",
            line=dict(color=AGUA_COLOR, width=2, dash="dot"),
            marker=dict(size=4),
            hovertemplate="WC: %{y:.1f}%<extra></extra>"
        ), secondary_y=True)
        fig_gor.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=300,
            margin=dict(t=10, b=40, l=55, r=55), hovermode="x unified"
        )
        fig_gor.update_yaxes(title_text="GOR (m³/m³)", secondary_y=False)
        fig_gor.update_yaxes(title_text="WC (%)", secondary_y=True)
        st.plotly_chart(fig_gor, use_container_width=True)

    # ── Agua producida ────────────────────────────────────────
    st.subheader("💧 Producción de Agua (m³/d)")
    fig_agua = go.Figure()
    fig_agua.add_trace(go.Bar(
        x=df["fecha"], y=df["agua_m3d"],
        name="Agua",
        marker_color=AGUA_COLOR,
        opacity=0.75,
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y:.1f} m³/d<extra></extra>"
    ))
    fig_agua.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", yaxis_title="m³/d", height=220,
        margin=dict(t=10, b=40, l=55, r=10), hovermode="x unified"
    )
    st.plotly_chart(fig_agua, use_container_width=True)

    # ── Tabla ─────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📋 Ver tabla de datos completa"):
        df_t = df[["fecha","oil_m3d","gas_mm3d","agua_m3d","gor","wc","cum_oil"]].copy()
        df_t.columns = ["Fecha","Petróleo (m³/d)","Gas (Mm³/d)","Agua (m³/d)",
                        "GOR (m³/m³)","WC (%)","Acum. Petróleo (m³)"]
        df_t["Fecha"] = df_t["Fecha"].dt.strftime("%b %Y")
        st.dataframe(df_t, use_container_width=True, hide_index=True)
        csv = df_t.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar CSV procesado", csv,
                           "et2043h_produccion.csv", "text/csv")

# ════════════════════════════════════════════════════════════
# TAB 2: TRAYECTORIA 3D
# ════════════════════════════════════════════════════════════
with tab2:

    col_3d, col_info = st.columns([3, 1])

    with col_info:
        st.subheader("🪨 Columna Estratigráfica")
        for s in STRAT:
            is_target = s["name"] == "VM Inferior"
            label = f"🎯 **{s['name']}**" if is_target else f"**{s['name']}**"
            st.markdown(
                f"<div style='border-left:3px solid {s['color']};padding:6px 10px;"
                f"margin-bottom:6px;background:{'#f7816611' if is_target else '#ffffff08'};"
                f"border-radius:0 6px 6px 0'>"
                f"{label}<br>"
                f"<span style='font-size:0.75rem;color:#8b949e'>"
                f"{s['top']:,}–{s['base']:,} m TVD</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        st.markdown("---")
        st.markdown("**Parámetros del modelo**")
        st.caption("📐 Azimut: N 85° E")
        st.caption("↗ Buzamiento: ~2° E")
        st.caption("⬇ KOP estimado: 1.500 m TVD")
        st.caption("🎯 Target: ~5.100 m TVD")
        st.caption("📏 Rama horiz. est.: 2.500 m")
        st.caption("📍 El Trapial Este, Neuquén")
        st.caption("🔢 ID Pozo: 164531")

    with col_3d:
        st.subheader("Vista 3D — Trayectoria + Estratigrafía")

        fig3d = go.Figure()

        for s in surfaces:
            fig3d.add_trace(go.Surface(
                x=s["xg"], y=s["yg"], z=s["Z"],
                surfacecolor=s["C"],
                colorscale=make_colorscale(s["color"]),
                opacity=0.55 if s["is_target"] else 0.22,
                showscale=False,
                name=s["name"],
                showlegend=True,
                hovertemplate=(
                    f"<b>{s['name']}</b><br>"
                    "E: %{x:.0f} m<br>N: %{y:.0f} m<br>"
                    "TVD: %{z:.0f} m<extra></extra>"
                ),
                lighting=dict(ambient=0.9, diffuse=0.3)
            ))

        xs, ys, zs = traj
        fig3d.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            name=NOMBRE_POZO,
            mode="lines",
            line=dict(color=POZO_COLOR, width=7),
            hovertemplate=(
                f"<b>{NOMBRE_POZO}</b><br>"
                "E: %{x:.0f} m<br>N: %{y:.0f} m<br>"
                "TVD: %{z:.0f} m<extra></extra>"
            )
        ))

        # Guía vertical punteada
        fig3d.add_trace(go.Scatter3d(
            x=[0, 0], y=[0, 0], z=[0, -1500],
            mode="lines",
            line=dict(color=POZO_COLOR, width=1, dash="dot"),
            showlegend=False, hoverinfo="skip"
        ))

        # Boca de pozo
        fig3d.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode="markers+text",
            text=[NOMBRE_POZO],
            textposition="top center",
            textfont=dict(color="#e6edf3", size=10),
            marker=dict(size=7, color=POZO_COLOR, symbol="diamond"),
            name="Boca de pozo",
            hovertemplate=f"<b>{NOMBRE_POZO}</b><br>Superficie<extra></extra>"
        ))

        fig3d.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8b949e", size=11),
            margin=dict(t=10, b=10, l=0, r=0),
            height=600,
            scene=dict(
                bgcolor="#0d1117",
                xaxis=dict(title="Este (m)",  gridcolor="#21262d", linecolor="#30363d"),
                yaxis=dict(title="Norte (m)", gridcolor="#21262d", linecolor="#30363d"),
                zaxis=dict(title="TVD (m)",   gridcolor="#21262d", linecolor="#30363d"),
                camera=dict(eye=dict(x=-1.6, y=-1.4, z=0.8)),
                aspectmode="manual",
                aspectratio=dict(x=2.2, y=0.8, z=1)
            ),
            legend=dict(bgcolor="#161b22", bordercolor="#30363d",
                        borderwidth=1, font=dict(size=10))
        )
        st.plotly_chart(fig3d, use_container_width=True)

        # ── Perfil vertical 2D ────────────────────────────────
        with st.expander("📐 Ver perfil vertical (Este vs TVD)"):
            dip = np.tan(2 * np.pi / 180)
            fig2d = go.Figure()
            xr = [-300, max(xs) + 300]
            for s in STRAT:
                tl = -(s["top"]  + xr[0]*dip); tr = -(s["top"]  + xr[1]*dip)
                bl = -(s["base"] + xr[0]*dip); br = -(s["base"] + xr[1]*dip)
                is_t = s["name"] == "VM Inferior"
                fig2d.add_trace(go.Scatter(
                    x=[xr[0], xr[1], xr[1], xr[0], xr[0]],
                    y=[tl, tr, br, bl, tl],
                    fill="toself",
                    fillcolor=hex_to_rgba(s["color"], 0.18 if is_t else 0.07),
                    line=dict(color=s["color"],
                              width=1.5 if is_t else 0.5,
                              dash="solid" if is_t else "dot"),
                    showlegend=False,
                    hovertemplate=f"<b>{s['name']}</b><extra></extra>"
                ))
                x_label = xr[0] + 150
                y_mid   = -(s["top"] + s["base"]) / 2 - x_label * dip
                fig2d.add_annotation(
                    x=x_label, y=y_mid, text=s["name"],
                    showarrow=False,
                    font=dict(color=s["color"], size=9),
                    xanchor="left"
                )

            fig2d.add_trace(go.Scatter(
                x=xs, y=zs, name=NOMBRE_POZO, mode="lines",
                line=dict(color=POZO_COLOR, width=2.5),
                hovertemplate=(
                    f"<b>{NOMBRE_POZO}</b><br>"
                    "E: %{x:.0f} m<br>TVD: %{y:.0f} m<extra></extra>"
                )
            ))

            fig2d.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=380,
                margin=dict(t=10, b=50, l=65, r=20),
                xaxis=dict(title="Desplazamiento Este (m)",
                           gridcolor="#21262d", zeroline=False),
                yaxis=dict(title="TVD (m)", gridcolor="#21262d", zeroline=False),
                hovermode="closest"
            )
            st.plotly_chart(fig2d, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Dashboard · Datos reales Capítulo IV · "
    "CHA.Nq.ET-2043(h) · Chevron Argentina · "
    "Desarrollado con Streamlit + Plotly · Cuenca Neuquina"
)
