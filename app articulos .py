import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import datetime
import json
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# =============================
# CONFIGURACIÓN BASE
# =============================
st.set_page_config(page_title="Asistente de Búsqueda Científica", layout="wide")
st.title("🔬 Asistente de Búsqueda Científica")

# --- Conexión a Supabase (solo para logs) ---
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

# --- URL del Webhook de n8n ---
WEBHOOK_URL = "https://eriks20252.app.n8n.cloud/webhook/busqueda-cientifica"

# =============================
# FUNCIONES AUXILIARES
# =============================

def generar_pdf(df, tema, resumen_estadistico):
    """Genera un PDF con los artículos y resumen estadístico."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("Asistente de Búsqueda Científica", styles["Title"]))
    content.append(Paragraph(f"Tema: <b>{tema}</b>", styles["Heading2"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("📊 Resumen estadístico:", styles["Heading3"]))
    for k, v in resumen_estadistico.items():
        content.append(Paragraph(f"{k}: {v}", styles["Normal"]))
    content.append(Spacer(1, 10))

    # Tabla de artículos
    content.append(Paragraph("📚 Artículos encontrados:", styles["Heading3"]))
    data = [["Título", "Autores", "Año", "Fuente"]]
    for _, r in df.iterrows():
        data.append([r["titulo"], r["autores"], str(r["año"]), r["fuente"]])
    table = Table(data, colWidths=[200, 150, 50, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    content.append(table)
    doc.build(content)
    buffer.seek(0)
    return buffer


def mostrar_estadistica(df):
    """Muestra estadísticas visuales."""
    st.subheader("📊 Estadística descriptiva")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total artículos", len(df))
    c2.metric("Fuentes únicas", df["fuente"].nunique())
    c3.metric("Años distintos", df["año"].nunique())

    df["año"] = pd.to_numeric(df["año"], errors="coerce")

    st.markdown("#### Distribución de publicaciones por año")
    fig = px.histogram(df, x="año", nbins=15, title="Publicaciones por año", color_discrete_sequence=["#636EFA"])
    st.plotly_chart(fig, use_container_width=True)

    if df["año"].notna().any():
        año_top = int(df["año"].mode().iloc[0])
        total_top = (df["año"] == año_top).sum()
        st.info(f"📅 Año con más publicaciones: {año_top} ({total_top} artículos)")

# =============================
# INTERFAZ PRINCIPAL
# =============================

tabs = st.tabs(["🔍 Nueva búsqueda", "📜 Historial"])

# ---------- TAB 1 ----------
with tabs[0]:
    with st.form("form_busqueda"):
        tema = st.text_input("📚 Tema de investigación", "")
        c1, c2 = st.columns(2)
        with c1:
            fecha_inicio = st.date_input("📅 Fecha inicio", datetime.date(2020,1,1))
        with c2:
            fecha_fin = st.date_input("📅 Fecha fin", datetime.date.today())
        idioma = st.selectbox("🌐 Idioma", ["en,es", "en", "es"])
        buscar = st.form_submit_button("🔍 Buscar artículos")

    if buscar and tema:
        with st.spinner("Buscando artículos con n8n..."):
            try:
                payload = {
                    "tema": tema,
                    "fechaInicio": str(fecha_inicio),
                    "fechaFin": str(fecha_fin),
                    "idioma": idioma
                }
                res = requests.post(WEBHOOK_URL, json=payload)
                res.raise_for_status()
                data = res.json()
                articles = [a.get("json", a) for a in data] if isinstance(data, list) else []

                if not articles:
                    st.warning("No se encontraron artículos.")
                else:
                    # Filtrar solo los que tengan título
                    clean_articles = []
                    for a in articles:
                        if isinstance(a, dict) and "titulo" in a and a["titulo"]:
                            clean_articles.append(a)
                    if not clean_articles:
                        st.warning("No se encontraron artículos válidos con título.")
                    else:
                        df = pd.DataFrame(clean_articles)
                        st.success(f"✅ {len(df)} artículos encontrados para '{tema}'")
                        
                        # Mostrar artículos estilo tarjeta
                        for _, r in df.iterrows():
                            with st.expander(f"📄 {r['titulo']} ({r.get('año', 'N/A')})"):
                                st.markdown(f"**Autores:** {r.get('autores', 'Desconocido')}")
                                st.markdown(f"**Fuente:** {r.get('fuente', 'N/A')}")
                                resumen = r.get('resumen', 'Sin resumen disponible')
                                st.markdown(f"**Resumen:** {resumen[:400]}...")
                                if r.get("url"):
                                    st.markdown(f"[🔗 Ver artículo]({r['url']})", unsafe_allow_html=True)

                        # Mostrar estadísticas
                        mostrar_estadistica(df)

                        # Resumen para PDF
                        resumen = {
                            "Artículos encontrados": len(df),
                            "Fuentes únicas": df["fuente"].nunique(),
                            "Años distintos": df["año"].nunique()
                        }

                        # Descargar PDF
                        pdf_buffer = generar_pdf(df, tema, resumen)
                        st.download_button(
                            label="📥 Descargar PDF de resultados",
                            data=pdf_buffer,
                            file_name=f"busqueda_{tema}.pdf",
                            mime="application/pdf"
                        )

                    
                    # Mostrar artículos
                    for _, r in df.iterrows():
                        with st.expander(f"📄 {r['titulo']} ({r['año']})"):
                            st.markdown(f"**Autores:** {r['autores']}")
                            st.markdown(f"**Fuente:** {r['fuente']}")
                            st.markdown(f"**Resumen:** {r['resumen'][:500]}...")
                            if r.get("url"):
                                st.markdown(f"[🔗 Ver artículo completo]({r['url']})", unsafe_allow_html=True)

                    mostrar_estadistica(df)

                    resumen = {
                        "Artículos encontrados": len(df),
                        "Fuentes únicas": df["fuente"].nunique(),
                        "Años distintos": df["año"].nunique()
                    }
                    pdf = generar_pdf(df, tema, resumen)
                    st.download_button("📥 Descargar PDF", pdf, file_name=f"busqueda_{tema}.pdf", mime="application/pdf")

            except Exception as e:
                st.error(f"❌ Error al buscar artículos: {e}")

# ---------- TAB 2 ----------
with tabs[1]:
    st.subheader("📜 Historial de búsquedas anteriores")
    try:
        res = supabase.table("search_logs").select("*").order("search_date", desc=True).execute()
        registros = res.data or []
        if not registros:
            st.info("No hay búsquedas registradas aún.")
        else:
            df_hist = pd.DataFrame(registros)
            if "search_date" in df_hist.columns:
                df_hist["search_date"] = pd.to_datetime(df_hist["search_date"])

            st.dataframe(df_hist[["search_date", "search_term", "idioma", "results_count"]])

            st.markdown("#### 📈 Estadísticas globales")
            fig1 = px.histogram(df_hist, x="search_term", y="results_count", title="Frecuencia de temas buscados")
            st.plotly_chart(fig1, use_container_width=True)
            fig2 = px.pie(df_hist, names="idioma", title="Idiomas utilizados")
            st.plotly_chart(fig2, use_container_width=True)

            selected = st.selectbox("🔎 Ver detalles de una búsqueda:", df_hist["search_term"].unique())
            if selected:
                detalle = df_hist[df_hist["search_term"] == selected].iloc[0]
                df_prev = pd.DataFrame(json.loads(detalle["results_data"]))
                st.success(f"📚 {len(df_prev)} artículos encontrados para '{selected}'")

                for _, r in df_prev.iterrows():
                    with st.expander(f"📑 {r['titulo']} ({r['año']})"):
                        st.markdown(f"**Autores:** {r['autores']}")
                        st.markdown(f"**Fuente:** {r['fuente']}")
                        st.markdown(f"**Resumen:** {r['resumen'][:500]}...")
                        if r.get("url"):
                            st.markdown(f"[🔗 Ver artículo completo]({r['url']})", unsafe_allow_html=True)

                mostrar_estadistica(df_prev)

    except Exception as e:
        st.error(f"Error al cargar historial: {e}")



