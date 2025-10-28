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

# Conexión a Supabase
url = st.secrets["https://ypdtrkvebwjiqlmryaoc.supabase.co"]
key = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlwZHRya3ZlYndqaXFsbXJ5YW9jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjEyNTIzNjEsImV4cCI6MjA3NjgyODM2MX0.cWzJQ59oY8xgZvBJ0I7a1a4XWXkRfeIdHbC3PSzVG4w"]
supabase: Client = create_client(url, key)

# URL del Webhook de n8n
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

    content.append(Paragraph(f"Asistente de Búsqueda Científica", styles["Title"]))
    content.append(Paragraph(f"Tema: <b>{tema}</b>", styles["Heading2"]))
    content.append(Spacer(1, 10))

    # Resumen estadístico
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
    """Genera estadísticas descriptivas visuales dentro de Streamlit."""
    st.subheader("📊 Estadística descriptiva")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total artículos", len(df))
    c2.metric("Fuentes únicas", df["fuente"].nunique())
    c3.metric("Años distintos", df["año"].nunique())

    df["año"] = pd.to_numeric(df["año"], errors="coerce")

    # Distribución por año
    st.markdown("#### Distribución de publicaciones por año")
    fig_year = px.histogram(df, x="año", nbins=15, title="Publicaciones por año", color_discrete_sequence=["#636EFA"])
    st.plotly_chart(fig_year, use_container_width=True)

    # Año más frecuente
    if df["año"].notna().any():
        año_mas_publicado = int(df["año"].mode().iloc[0])
        total_año = (df["año"] == año_mas_publicado).sum()
        st.info(f"📆 Año con más publicaciones: {año_mas_publicado} ({total_año} artículos)")

    # Palabras clave más comunes
    if "palabras_clave" in df.columns:
        keywords = []
        for kw in df["palabras_clave"].dropna():
            keywords.extend([k.strip() for k in kw.split(",") if k.strip()])
        if keywords:
            kw_df = pd.DataFrame({"Palabra clave": keywords})
            top_kw = kw_df["Palabra clave"].value_counts().head(10)
            st.markdown("#### Palabras clave más frecuentes")
            fig_kw = px.bar(
                x=top_kw.index, y=top_kw.values,
                title="Palabras clave más frecuentes",
                color_discrete_sequence=["#EF553B"]
            )
            st.plotly_chart(fig_kw, use_container_width=True)

# =============================
# INTERFAZ PRINCIPAL
# =============================

tabs = st.tabs(["🔍 Búsqueda", "📜 Historial"])

# ---------- TAB 1: Búsqueda ----------
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
        with st.spinner("Buscando artículos..."):
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
                    st.warning("⚠️ No se encontraron artículos para ese tema.")
                else:
                    df = pd.DataFrame(articles)
                    st.success(f"✅ {len(df)} artículos encontrados para '{tema}'")

                    # Guardar búsqueda en Supabase
                    supabase.table("search_logs").insert({
                        "search_term": tema,
                        "fecha_inicio": str(fecha_inicio),
                        "fecha_fin": str(fecha_fin),
                        "idioma": idioma,
                        "results_count": len(df),
                        "results_data": json.dumps(articles)
                    }).execute()

                    st.markdown("### 📄 Resultados encontrados")
                    for _, r in df.iterrows():
                        with st.expander(f"📑 {r['titulo']} ({r['año']})"):
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

                    pdf_buffer = generar_pdf(df, tema, resumen)
                    st.download_button(
                        label="📥 Descargar PDF de resultados",
                        data=pdf_buffer,
                        file_name=f"busqueda_{tema}.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"❌ Error al realizar la búsqueda: {e}")

# ---------- TAB 2: Historial ----------
with tabs[1]:
    st.subheader("📜 Historial de búsquedas previas")
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
        fig1 = px.histogram(df_hist, x="search_term", y="results_count", title="Frecuencia de temas buscados", color_discrete_sequence=["#00CC96"])
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.pie(df_hist, names="idioma", title="Idiomas utilizados")
        st.plotly_chart(fig2, use_container_width=True)

        # 🔎 Nuevo: ver detalles de cada búsqueda pasada
        st.markdown("### 🔎 Ver detalles de una búsqueda anterior")
        selected_search = st.selectbox("Selecciona una búsqueda para ver sus artículos:", df_hist["search_term"].unique())

        if selected_search:
            detalle = df_hist[df_hist["search_term"] == selected_search].iloc[0]
            articles_prev = json.loads(detalle["results_data"])
            df_prev = pd.DataFrame(articles_prev)
            st.success(f"📚 {len(df_prev)} artículos encontrados para '{selected_search}'")

            for _, r in df_prev.iterrows():
                with st.expander(f"📑 {r['titulo']} ({r['año']})"):
                    st.markdown(f"**Autores:** {r['autores']}")
                    st.markdown(f"**Fuente:** {r['fuente']}")
                    st.markdown(f"**Resumen:** {r['resumen'][:500]}...")
                    if r.get("url"):
                        st.markdown(f"[🔗 Ver artículo completo]({r['url']})", unsafe_allow_html=True)

            mostrar_estadistica(df_prev)

            resumen_prev = {
                "Artículos encontrados": len(df_prev),
                "Fuentes únicas": df_prev["fuente"].nunique(),
                "Años distintos": df_prev["año"].nunique()
            }

            pdf_prev = generar_pdf(df_prev, selected_search, resumen_prev)
            st.download_button(
                label=f"📥 Descargar PDF de '{selected_search}'",
                data=pdf_prev,
                file_name=f"busqueda_{selected_search}.pdf",
                mime="application/pdf"
            )

        # 📘 PDF global del historial
        resumen_global = {
            "Total búsquedas": len(df_hist),
            "Artículos totales": df_hist["results_count"].sum(),
            "Temas únicos": df_hist["search_term"].nunique()
        }
        pdf_hist = generar_pdf(df_hist.rename(columns={
            "search_term": "titulo",
            "idioma": "fuente",
            "results_count": "año",
            "search_date": "autores"
        }), "Historial global", resumen_global)
        st.download_button("📥 Descargar informe global PDF", pdf_hist, "historial_busquedas.pdf", mime="application/pdf")

