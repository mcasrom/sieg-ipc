#!/usr/bin/env python3
"""
app.py
SIEG Monitor IPC · Inflación y Precios España

Dashboard IPC y análisis de inflación.

Autor : M. Castillo · mybloggingnotes@gmail.com
© 2026 M. Castillo
"""

import os
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import duckdb
import altair as alt
from datetime import datetime, date

st.set_page_config(
    page_title="SIEG Monitor IPC · Inflación España",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Detección entorno ─────────────────────────────────────
_local  = os.path.expanduser("~/sieg-ipc")
_cloud  = "/mount/src/sieg-ipc"
_script = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_script)
BASE_DIR = next(
    (p for p in [_local, _cloud, _parent]
     if os.path.exists(os.path.join(p, "data", "exports"))),
    _parent
)
DB_PATH = os.path.join(BASE_DIR, "data", "processed", "ipc.duckdb")
EXP_DIR = os.path.join(BASE_DIR, "data", "exports")

# ── Logo ──────────────────────────────────────────────────
st.markdown("""
<svg width='100%' viewBox='0 0 680 110' xmlns='http://www.w3.org/2000/svg'>
<style>
@keyframes scan{0%{opacity:.1}50%{opacity:.35}100%{opacity:.1}}
.sc{animation:scan 3s ease-in-out infinite}
</style>
<rect width='680' height='110' rx='4' fill='#0a0e0a' stroke='#1a2e1a'/>
<rect width='680' height='110' rx='4' fill='none' stroke='#00ff41' stroke-width='0.5' opacity='0.25'/>
<line x1='0' y1='26' x2='680' y2='26' stroke='#00ff41' stroke-width='0.3' opacity='0.15'/>
<circle cx='16' cy='13' r='4' fill='#ff5f57'/>
<circle cx='30' cy='13' r='4' fill='#febc2e'/>
<circle cx='44' cy='13' r='4' fill='#28c840'/>
<text x='340' y='18' text-anchor='middle' font-family='monospace' font-size='9' fill='#00ff41' opacity='0.35'>sieg-monitor-ipc — inflacion-precios-espana</text>
<rect x='14' y='36' width='652' height='1' fill='#00ff41' opacity='0.06' class='sc'/>
<rect x='14' y='62' width='652' height='1' fill='#00ff41' opacity='0.06' class='sc' style='animation-delay:.8s'/>
<text x='18' y='50' font-family='monospace' font-size='9' fill='#00ff41' opacity='0.45'>root@sieg:~$</text>
<text x='100' y='50' font-family='monospace' font-size='9' fill='#00ff41'>./monitor --fuente=INE --indicador=IPC --series=10 --historico=36m</text>
<text x='18' y='66' font-family='monospace' font-size='8' fill='#4ade80' opacity='0.65'>[+] API Instituto Nacional de Estadistica | 10 categorias | Historico 3 años</text>
<text x='18' y='88' font-family='monospace' font-size='18' font-weight='bold' fill='#00ff41' letter-spacing='3'>SIEG MONITOR IPC</text>
<text x='290' y='88' font-family='monospace' font-size='11' fill='#00cc33' letter-spacing='2'>Inflación · Precios · España</text>
<text x='290' y='103' font-family='monospace' font-size='9' fill='#009922' opacity='0.7'>Datos oficiales Instituto Nacional de Estadística</text>
<text x='18' y='103' font-family='monospace' font-size='7' fill='#00ff41' opacity='0.3'>© 2026 M.Castillo · mybloggingnotes@gmail.com</text>
</svg>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.markdown("""
<div style='padding:0.4rem 0 0.8rem 0; border-bottom:1px solid rgba(0,255,65,0.15); margin-bottom:0.8rem'>
    <div style='font-size:0.65rem; color:#00cc33; font-weight:600; letter-spacing:2px'>SIEG OSINT</div>
    <div style='font-size:0.95rem; font-weight:600; color:#00ff41'>Monitor IPC</div>
    <div style='font-size:0.65rem; color:#4a7a4a'>Inflación · Precios · España</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style='font-size:0.75rem; line-height:1.9; opacity:0.75; margin-bottom:8px'>
    <div style='font-weight:600; margin-bottom:6px; font-size:0.8rem; color:#00ff41'>🛰️ Red SIEG OSINT</div>
    <a href='https://mcasrom.github.io/sieg-osint' target='_blank' style='display:block; color:#4ade80; text-decoration:none; margin-bottom:4px'>🌐 Portal SIEG OSINT</a>
    <a href='https://politica-nacional-osint.streamlit.app' target='_blank' style='display:block; color:#4ade80; text-decoration:none; margin-bottom:4px'>📊 SIEG Política Nacional</a>
    <a href='https://fake-news-narrative.streamlit.app' target='_blank' style='display:block; color:#4ade80; text-decoration:none; margin-bottom:4px'>📡 Narrative Radar</a>
    <a href='https://sieg-radar-electoral.streamlit.app' target='_blank' style='display:block; color:#4ade80; text-decoration:none; margin-bottom:4px'>🗳️ España Vota 2026</a>
    <a href='https://sieg-monitor-boe.streamlit.app' target='_blank' style='display:block; color:#4ade80; text-decoration:none; margin-bottom:4px'>📋 Monitor BOE</a>
    <a href='https://sieg-energia.streamlit.app' target='_blank' style='display:block; color:#4ade80; text-decoration:none; margin-bottom:4px'>⚡ Monitor Energético</a>
    <a href='https://t.me/sieg_politica' target='_blank' style='display:block; color:#4ade80; text-decoration:none'>📢 Canal @sieg_politica</a>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style='text-align:center; padding:6px 0; margin-bottom:8px'>
    <a href='https://ko-fi.com/m_castillo' target='_blank'
       style='display:inline-block; background:#FF5E5B; color:white;
              font-weight:600; font-size:0.75rem; padding:6px 14px;
              border-radius:16px; text-decoration:none'>☕ Buy me a coffee</a>
    <div style='font-size:0.65rem; opacity:0.4; margin-top:3px'>Apoya SIEG OSINT</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='font-size:0.65rem; opacity:0.35; text-align:center; font-family:monospace'>
    © 2026 M. Castillo<br>
    <a href='mailto:mybloggingnotes@gmail.com' style='color:inherit'>mybloggingnotes@gmail.com</a><br>
    Datos: Instituto Nacional de Estadística
</div>
""", unsafe_allow_html=True)

# ── Carga de datos ────────────────────────────────────────
@st.cache_data(ttl=3600)
def cargar_datos():
    try:
        if os.path.exists(DB_PATH):
            conn = duckdb.connect(DB_PATH, read_only=True)
            df_ultimo  = conn.execute("SELECT * FROM ipc_ultimo ORDER BY valor DESC").df()
            df_datos   = conn.execute("SELECT * FROM ipc_datos WHERE fecha >= '2023-01-01' ORDER BY categoria, fecha").df()
            df_general = conn.execute("SELECT * FROM ipc_datos WHERE categoria = 'IPC General' ORDER BY fecha").df()
            conn.close()
        else:
            df_ultimo  = pd.read_parquet(os.path.join(EXP_DIR, "ipc_ultimo.parquet")) if os.path.exists(os.path.join(EXP_DIR, "ipc_ultimo.parquet")) else pd.DataFrame()
            df_datos   = pd.read_parquet(os.path.join(EXP_DIR, "ipc_datos.parquet")) if os.path.exists(os.path.join(EXP_DIR, "ipc_datos.parquet")) else pd.DataFrame()
            df_general = pd.read_parquet(os.path.join(EXP_DIR, "ipc_general.parquet")) if os.path.exists(os.path.join(EXP_DIR, "ipc_general.parquet")) else pd.DataFrame()
        # Veracidad
        try:
            if os.path.exists(DB_PATH):
                df_veracidad = conn.execute("SELECT * FROM ipc_veracidad ORDER BY fecha DESC").df() if 'conn' in dir() else pd.DataFrame()
            else:
                vpath = os.path.join(EXP_DIR, "ipc_veracidad.parquet")
                df_veracidad = pd.read_parquet(vpath) if os.path.exists(vpath) else pd.DataFrame()
        except:
            df_veracidad = pd.DataFrame()
        return df_ultimo, df_datos, df_general, df_veracidad
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_ultimo, df_datos, df_general, df_veracidad = cargar_datos()

# ── Tabs ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Resumen IPC",
    "📈 Evolución histórica",
    "🛒 Cesta de la compra",
    "🔮 Predicción tendencia",
    "🔍 Veracidad INE vs Eurostat",
    "📖 Guía"
])

# ── Tab 1: Resumen ────────────────────────────────────────
with tab1:
    st.header("📊 IPC España — Último dato disponible")

    if df_ultimo.empty:
        st.info("Sin datos. Ejecuta el pipeline primero.")
    else:
        df_ultimo["fecha"] = pd.to_datetime(df_ultimo["fecha"], errors="coerce")
        ultimo_mes = df_ultimo.iloc[0]
        fecha_str  = ultimo_mes["fecha"].strftime("%B %Y") if pd.notna(ultimo_mes["fecha"]) else "—"

        st.caption(f"Datos INE — {fecha_str}")

        # KPIs principales
        ipc_gen  = df_ultimo[df_ultimo["categoria"] == "IPC General"]["valor"].values
        ipc_sub  = df_ultimo[df_ultimo["categoria"] == "IPC Subyacente"]["valor"].values
        ipc_ali  = df_ultimo[df_ultimo["categoria"] == "Alimentos y bebidas"]["valor"].values
        ipc_alq  = df_ultimo[df_ultimo["categoria"] == "Alquiler vivienda"]["valor"].values

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 IPC General", f"{ipc_gen[0]:.1f}%"  if len(ipc_gen) > 0 else "—",
                  "variación anual")
        c2.metric("🎯 Subyacente",  f"{ipc_sub[0]:.1f}%"  if len(ipc_sub) > 0 else "—",
                  "sin energía ni alimentos frescos")
        c3.metric("🛒 Alimentación", f"{ipc_ali[0]:.1f}%" if len(ipc_ali) > 0 else "—",
                  "alimentos y bebidas")
        c4.metric("🏠 Alquiler",    f"{ipc_alq[0]:.1f}%"  if len(ipc_alq) > 0 else "—",
                  "vivienda en alquiler")

        st.markdown("---")

        # Gráfico barras todas las categorías
        df_chart = df_ultimo.copy()
        df_chart["color_tipo"] = df_chart["valor"].apply(
            lambda v: "alto" if v > 3 else ("medio" if v > 1.5 else ("bajo" if v >= 0 else "negativo"))
        )
        color_scale = alt.Scale(
            domain=["alto", "medio", "bajo", "negativo"],
            range=["#ef4444", "#f97316", "#22c55e", "#3b82f6"]
        )

        chart = alt.Chart(df_chart).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("valor:Q", title="Variación anual (%)"),
            y=alt.Y("categoria:N", sort="-x", title="Categoría"),
            color=alt.Color("color_tipo:N", scale=color_scale, legend=None),
            tooltip=["categoria:N", alt.Tooltip("valor:Q", title="IPC %", format=".1f"),
                     alt.Tooltip("variacion:Q", title="Δ mes anterior", format=".2f")]
        ).properties(height=320, title=f"IPC por categoría — {fecha_str}")

        # Línea cero
        linea_cero = alt.Chart(pd.DataFrame({"v": [0]})).mark_rule(
            color="#ffffff", opacity=0.3, strokeDash=[4, 4]
        ).encode(x="v:Q")

        st.altair_chart(chart + linea_cero, use_container_width=True)

        # Tabla detalle
        st.subheader("📋 Detalle por categoría")
        df_tabla = df_ultimo[["categoria", "valor", "variacion", "fecha"]].copy()
        df_tabla["fecha"]     = pd.to_datetime(df_tabla["fecha"]).dt.strftime("%m/%Y")
        df_tabla["valor"]     = df_tabla["valor"].round(1).astype(str) + "%"
        df_tabla["variacion"] = df_tabla["variacion"].round(2).astype(str) + "pp"
        df_tabla.columns      = ["Categoría", "IPC anual", "Δ mes anterior", "Fecha dato"]
        st.dataframe(df_tabla, use_container_width=True, hide_index=True)

# ── Tab 2: Evolución histórica ────────────────────────────
with tab2:
    st.header("📈 Evolución histórica del IPC")

    if df_datos.empty:
        st.info("Sin datos históricos.")
    else:
        df_datos["fecha"] = pd.to_datetime(df_datos["fecha"], errors="coerce")

        # Selector de categorías
        cats = sorted(df_datos["categoria"].unique().tolist())
        cats_sel = st.multiselect(
            "Categorías a mostrar:",
            options=cats,
            default=["IPC General", "IPC Subyacente", "Alimentos y bebidas", "Alquiler vivienda"]
        )

        if cats_sel:
            df_hist = df_datos[df_datos["categoria"].isin(cats_sel)].copy()

            chart_hist = alt.Chart(df_hist).mark_line(point=True).encode(
                x=alt.X("fecha:T", title="Fecha"),
                y=alt.Y("valor:Q", title="Variación anual (%)"),
                color=alt.Color("categoria:N", title="Categoría"),
                tooltip=["fecha:T", "categoria:N",
                         alt.Tooltip("valor:Q", title="IPC %", format=".1f")]
            ).properties(height=380, title="Evolución IPC por categoría (últimos 3 años)")

            linea = alt.Chart(pd.DataFrame({"v": [0]})).mark_rule(
                color="#ffffff", opacity=0.2, strokeDash=[4, 4]
            ).encode(y="v:Q")

            st.altair_chart(chart_hist + linea, use_container_width=True)

# ── Tab 3: Cesta compra ───────────────────────────────────
with tab3:
    st.header("🛒 Impacto en tu cesta de la compra")
    st.caption("Calcula cuánto más pagas hoy vs hace un año por tus gastos habituales")

    if df_ultimo.empty:
        st.info("Sin datos disponibles.")
    else:
        st.markdown("### Introduce tus gastos mensuales aproximados:")

        col1, col2 = st.columns(2)
        with col1:
            gasto_alimentacion = st.number_input("🛒 Alimentación (€/mes)", 0, 2000, 400, step=50)
            gasto_vivienda     = st.number_input("🏠 Alquiler vivienda (€/mes)", 0, 3000, 800, step=50)
            gasto_transporte   = st.number_input("🚗 Transporte (€/mes)", 0, 1000, 150, step=25)
        with col2:
            gasto_salud        = st.number_input("💊 Medicamentos y salud (€/mes)", 0, 500, 50, step=10)
            gasto_servicios    = st.number_input("📱 Servicios (teléfono, internet...) (€/mes)", 0, 500, 100, step=10)
            gasto_energia      = st.number_input("⚡ Energía (luz, gas) (€/mes)", 0, 500, 120, step=10)

        # Calcular impacto
        def get_ipc(cat):
            v = df_ultimo[df_ultimo["categoria"] == cat]["valor"].values
            return v[0] / 100 if len(v) > 0 else 0.03

        gastos = {
            "🛒 Alimentación":    (gasto_alimentacion, get_ipc("Alimentos y bebidas")),
            "🏠 Alquiler":        (gasto_vivienda,     get_ipc("Alquiler vivienda")),
            "🚗 Transporte":      (gasto_transporte,   get_ipc("Transporte carretera")),
            "💊 Medicamentos":    (gasto_salud,         get_ipc("Medicamentos")),
            "📱 Servicios":       (gasto_servicios,    get_ipc("Servicios")),
            "⚡ Energía":         (gasto_energia,      get_ipc("Electricidad gas")),
        }

        total_actual  = sum(g for g, _ in gastos.values())
        total_encarec = sum(g * ipc for g, ipc in gastos.values())
        total_hace_un_anyo = total_actual - total_encarec

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Gasto mensual actual", f"{total_actual:,.0f} €")
        c2.metric("📅 Hace un año equivalía a", f"{total_hace_un_anyo:,.0f} €")
        c3.metric("📈 Encarecimiento anual", f"{total_encarec:,.0f} €",
                  f"{total_encarec/total_hace_un_anyo*100:.1f}% más caro" if total_hace_un_anyo > 0 else "")

        # Desglose
        rows = []
        for concepto, (gasto, ipc) in gastos.items():
            encarec = gasto * ipc
            rows.append({"Concepto": concepto, "Gasto actual (€)": round(gasto, 0),
                         "Encarecimiento anual (€)": round(encarec, 2),
                         "IPC categoría (%)": round(ipc * 100, 1)})
        df_desglose = pd.DataFrame(rows)
        st.dataframe(df_desglose, use_container_width=True, hide_index=True)

# ── Tab 4: Predicción ─────────────────────────────────────
with tab4:
    st.header("🔮 Predicción tendencia IPC")
    st.caption("Regresión lineal sobre datos históricos INE — orientativo")

    if df_general.empty or len(df_general) < 6:
        st.info("Se necesitan al menos 6 meses de datos para la predicción.")
    else:
        import numpy as np
        from sklearn.linear_model import LinearRegression

        df_general["fecha"] = pd.to_datetime(df_general["fecha"], errors="coerce")
        df_general = df_general.dropna(subset=["fecha"]).sort_values("fecha")

        # Modelo
        X = np.arange(len(df_general)).reshape(-1, 1)
        y = df_general["valor"].values
        model = LinearRegression()
        model.fit(X, y)
        r2 = model.score(X, y)

        # Predicción próximos 6 meses
        n = len(df_general)
        X_fut = np.arange(n, n + 6).reshape(-1, 1)
        y_fut = model.predict(X_fut)

        # Fechas futuras
        ultima_fecha = df_general["fecha"].iloc[-1]
        fechas_fut   = pd.date_range(start=ultima_fecha, periods=7, freq="MS")[1:]

        df_pred = pd.DataFrame({
            "fecha": fechas_fut,
            "valor": y_fut.round(2),
            "tipo":  "Predicción"
        })
        df_hist_plot = df_general[["fecha", "valor"]].copy()
        df_hist_plot["tipo"] = "Histórico"

        df_plot = pd.concat([df_hist_plot, df_pred], ignore_index=True)

        color_scale = alt.Scale(
            domain=["Histórico", "Predicción"],
            range=["#00cc33", "#facc15"]
        )
        chart_pred = alt.Chart(df_plot).mark_line(point=True).encode(
            x=alt.X("fecha:T", title="Fecha"),
            y=alt.Y("valor:Q", title="IPC General (%)"),
            color=alt.Color("tipo:N", scale=color_scale, title=""),
            strokeDash=alt.StrokeDash("tipo:N",
                scale=alt.Scale(domain=["Histórico", "Predicción"], range=[[1,0],[4,2]])),
            tooltip=["fecha:T", alt.Tooltip("valor:Q", format=".2f"), "tipo:N"]
        ).properties(height=320, title="IPC General — Histórico y predicción próximos 6 meses")

        st.altair_chart(chart_pred, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("📊 IPC actual", f"{y[-1]:.1f}%")
        c2.metric("🔮 Predicción 6 meses", f"{y_fut[-1]:.1f}%")
        c3.metric("📐 R² del modelo", f"{r2:.3f}")

        st.dataframe(df_pred[["fecha", "valor"]].rename(
            columns={"fecha": "Mes", "valor": "IPC predicho (%)"}
        ).assign(Mes=lambda x: x["Mes"].dt.strftime("%m/%Y")),
            use_container_width=True, hide_index=True)

        st.info(
            f"⚠️ Predicción basada en regresión lineal simple sobre {len(df_general)} meses históricos. "
            f"El IPC real depende de factores macroeconómicos no modelados. R²={r2:.3f}"
        )

# ── Tab 5: Guía ───────────────────────────────────────────
with tab5:
    st.header("🔍 Veracidad IPC — INE vs Eurostat")
    st.caption("Comparativa entre el IPC oficial del INE y el HICP armonizado de Eurostat")

    st.markdown("""
> ⚠️ **Nota metodológica:** El IPC del INE y el HICP de Eurostat miden conceptos similares
> pero con metodologías distintas. Divergencias de hasta 0.3pp son normales por diferencias
> en la cesta de referencia, ponderaciones y tratamiento de servicios.
> Divergencias superiores a 0.5pp merecen análisis adicional.
    """)

    if df_veracidad.empty:
        st.info("Sin datos de veracidad. Ejecuta scripts/fetch_eurostat.py primero.")
    else:
        import pandas as pd
        df_veracidad["fecha"] = pd.to_datetime(df_veracidad["fecha"], errors="coerce")

        # KPIs
        n_alertas = len(df_veracidad[df_veracidad["alerta"] == True])
        div_media = df_veracidad["divergencia"].mean()
        div_max   = df_veracidad["divergencia"].abs().max()
        ultimo    = df_veracidad.iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 Meses comparados", len(df_veracidad))
        c2.metric("⚠️ Alertas divergencia", n_alertas)
        c3.metric("📐 Divergencia media", f"{div_media:+.2f}pp")
        c4.metric("📈 Divergencia máxima", f"{div_max:.2f}pp")

        st.markdown("---")

        # Gráfico comparativo
        import altair as alt

        df_chart = df_veracidad.copy()
        df_ine = df_chart[["fecha", "ine_valor"]].rename(columns={"ine_valor": "valor"})
        df_ine["fuente"] = "INE (oficial)"
        df_eur = df_chart[["fecha", "eurostat_valor"]].rename(columns={"eurostat_valor": "valor"})
        df_eur["fuente"] = "Eurostat HICP"
        df_plot = pd.concat([df_ine, df_eur])

        color_scale = alt.Scale(
            domain=["INE (oficial)", "Eurostat HICP"],
            range=["#00cc33", "#3b82f6"]
        )

        chart = alt.Chart(df_plot).mark_line(point=True).encode(
            x=alt.X("fecha:T", title="Fecha"),
            y=alt.Y("valor:Q", title="IPC General (%)"),
            color=alt.Color("fuente:N", scale=color_scale, title="Fuente"),
            tooltip=["fecha:T", "fuente:N", alt.Tooltip("valor:Q", format=".2f")]
        ).properties(height=300, title="IPC General: INE vs Eurostat HICP")

        st.altair_chart(chart, use_container_width=True)

        # Divergencia
        chart_div = alt.Chart(df_chart).mark_bar().encode(
            x=alt.X("fecha:T", title="Fecha"),
            y=alt.Y("divergencia:Q", title="Divergencia INE - Eurostat (pp)"),
            color=alt.condition(
                alt.datum.divergencia > 0,
                alt.value("#00cc33"),
                alt.value("#ef4444")
            ),
            tooltip=["fecha:T", alt.Tooltip("divergencia:Q", format="+.2f"), "nivel:N"]
        ).properties(height=200, title="Divergencia INE vs Eurostat (pp) — verde=INE mayor, rojo=Eurostat mayor")

        linea_cero = alt.Chart(pd.DataFrame({"v": [0]})).mark_rule(
            color="#ffffff", opacity=0.3, strokeDash=[4, 4]
        ).encode(y="v:Q")

        st.altair_chart(chart_div + linea_cero, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Detalle mensual")

        df_tabla = df_veracidad[["fecha", "ine_valor", "eurostat_valor", "divergencia", "nivel", "alerta"]].copy()
        df_tabla["fecha"] = df_tabla["fecha"].dt.strftime("%m/%Y")
        df_tabla["alerta"] = df_tabla["alerta"].map({True: "⚠️ Sí", False: "✅ No"})
        df_tabla.columns = ["Mes", "INE (%)", "Eurostat (%)", "Divergencia (pp)", "Nivel", "Alerta"]
        st.dataframe(df_tabla, use_container_width=True, hide_index=True)

        st.markdown("""
---
**Interpretación:**
- 🟢 **OK** — Diferencia < 0.2pp — normal, diferencias metodológicas menores
- 🟡 **BAJA** — Diferencia 0.2-0.5pp — revisar metodología de cálculo
- 🟠 **MEDIA** — Diferencia 0.5-1.0pp — divergencia significativa
- 🔴 **ALTA** — Diferencia > 1.0pp — divergencia muy relevante, posible sesgo
        """)

with tab6:
    st.header("📖 Guía de uso")
    st.markdown("""
## SIEG Monitor IPC · Inflación España

Monitor oficial del Índice de Precios de Consumo (IPC) español.

### ¿Qué es el IPC?
El IPC mide la evolución de los precios de los bienes y servicios que consume
la población española. Un IPC del 3% significa que los precios son un 3% más
caros que hace un año.

### Fuente de datos
- **API INE** (Instituto Nacional de Estadística) — datos oficiales
- Actualización: mensual (cuando el INE publica nuevos datos)
- Histórico: 3 años (36 meses)

### Categorías monitorizadas
| Categoría | Descripción |
|---|---|
| IPC General | Índice global de todos los bienes y servicios |
| IPC Subyacente | Sin energía ni alimentos frescos |
| Alimentos y bebidas | Toda la cesta de alimentación |
| Alquiler vivienda | Precio del alquiler residencial |
| Electricidad y gas | Energía doméstica |
| Servicios | Telefonía, internet, hostelería |
| Transporte | Carretera, ferrocarril, aéreo |
| Medicamentos | Productos farmacéuticos |

### Red SIEG OSINT
Monitor IPC forma parte del ecosistema SIEG OSINT España.

---
© 2026 M. Castillo · mybloggingnotes@gmail.com ·
[Portal SIEG OSINT](https://mcasrom.github.io/sieg-osint)
    """)

st.markdown("---")
st.markdown("""
<div style='text-align:center; font-size:0.72rem; opacity:0.35; font-family:monospace'>
    SIEG Monitor IPC · Inflación España · © 2026 M. Castillo ·
    Datos: <a href='https://www.ine.es' target='_blank' style='color:inherit'>Instituto Nacional de Estadística</a>
</div>
""", unsafe_allow_html=True)
