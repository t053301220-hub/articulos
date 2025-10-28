# app.py
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
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

# URL del Webhook de n8n
WEBHOOK_URL = "https://locopro0628.app.n8n.cloud/webhook/busqueda-cientifica"

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

    st.markdown("#### Distribución de publicaciones por año")
    st.plotly_chart(px.histogram(df, x="año", nbins=15, title="Publicaciones por año"), use_container_width=True)

    if "palabras_clave" in df.columns:
        keywords = []
        for kw in df["palabras_clave"].dropna():
            keywords.extend([k.strip() for k in kw.split(",") if k.strip()])
        if keywords:
            kw_df = pd.DataFrame({"Palabra clave": keywords})
            top_kw = kw_df["Palabra clave"].value_counts().head(10)
            st.markdown("#### Palabras clave más frecuentes")
            st.plotly_chart(px.bar(
                x=top_kw.index, y=top_kw.values,
                title="Palabras clave más frecuentes"
            ), use_container_width=True)

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
                data = res.json()
                articles = [a["json"] for a in data]

                if not articles:
                    st.warning("No se encontraron artículos.")
                else:
                    df = pd.DataFrame(articles)
                    st.success(f"✅ {len(df)} artículos encontrados")

                    # Guardar en Supabase
                    supabase.table("search_logs").insert({
                        "search_term": tema,
                        "fecha_inicio": str(fecha_inicio),
                        "fecha_fin": str(fecha_fin),
                        "idioma": idioma,
                        "results_count": len(df),
                        "results_data": json.dumps(articles)
                    }).execute()

                    # Mostrar artículos estilo tarjeta
                    for _, r in df.iterrows():
                        with st.expander(f"📄 {r['titulo']} ({r['año']})"):
                            st.markdown(f"**Autores:** {r['autores']}")
                            st.markdown(f"**Fuente:** {r['fuente']}")
                            st.markdown(f"**Resumen:** {r['resumen'][:400]}...")
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

# ---------- TAB 2: Historial ----------
with tabs[1]:
    st.subheader("📜 Historial de búsquedas")
    res = supabase.table("search_logs").select("*").order("search_date", desc=True).execute()
    registros = res.data or []

    if not registros:
        st.info("No hay búsquedas registradas aún.")
    else:
        df_hist = pd.DataFrame(registros)
        df_hist["search_date"] = pd.to_datetime(df_hist["search_date"])
        st.dataframe(df_hist[["search_date", "search_term", "idioma", "results_count"]])

        st.markdown("#### Estadísticas globales")
        fig1 = px.histogram(df_hist, x="search_term", y="results_count", title="Frecuencia de temas buscados")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.pie(df_hist, names="idioma", title="Idiomas utilizados")
        st.plotly_chart(fig2, use_container_width=True)

        # Descargar reporte global
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
