# =============================
# app.py — Asistente de Búsqueda Científica
# =============================
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import datetime
import json

# =============================
# CONFIGURACIÓN BASE
# =============================
st.set_page_config(page_title="Asistente de Búsqueda Científica", layout="wide")
st.title("🔬 Asistente de Búsqueda Científica")

# Supabase (desde Settings > Secrets en Streamlit Cloud)
SUPABASE_URL = st.secrets["supabase_url"]
SUPABASE_KEY = st.secrets["supabase_key"]

# URL del webhook n8n
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

    content.append(Paragraph("🔬 Asistente de Búsqueda Científica", styles["Title"]))
    content.append(Paragraph(f"Tema: <b>{tema}</b>", styles["Heading2"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("📊 Resumen estadístico:", styles["Heading3"]))
    for k, v in resumen_estadistico.items():
        content.append(Paragraph(f"{k}: {v}", styles["Normal"]))
    content.append(Spacer(1, 10))

    data = [["Título", "Autores", "Año", "Fuente"]]
    for _, r in df.iterrows():
        data.append([r["titulo"], r["autores"], str(r["año"]), r["fuente"]])
    table = Table(data, colWidths=[200, 150, 50, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
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
            top_kw = pd.Series(keywords).value_counts().head(10)
            st.markdown("#### Palabras clave más frecuentes")
            st.plotly_chart(px.bar(
                x=top_kw.index, y=top_kw.values, title="Palabras clave más frecuentes"
            ), use_container_width=True)

# =============================
# INTERFAZ PRINCIPAL
# =============================
st.markdown("#### Introduce los parámetros de búsqueda")

tema = st.text_input("📚 Tema de investigación")
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("📅 Fecha inicio", datetime.date(2020, 1, 1))
with col2:
    fecha_fin = st.date_input("📅 Fecha fin", datetime.date.today())
idioma = st.selectbox("🌐 Idioma", ["en,es", "en", "es"])

if st.button("🔍 Buscar artículos"):
    if not tema:
        st.warning("Por favor, ingresa un tema de investigación.")
    else:
        with st.spinner("Buscando artículos..."):
            try:
                payload = {
                    "tema": tema,
                    "fechaInicio": str(fecha_inicio),
                    "fechaFin": str(fecha_fin),
                    "idioma": idioma
                }
                res = requests.post(WEBHOOK_URL, json=payload)
                if res.status_code != 200:
                    st.error(f"❌ Error del servidor ({res.status_code}): {res.text}")
                else:
                    data = res.json()
                    articles = [a for a in data if isinstance(a, dict) and "titulo" in a and a["titulo"]]

                    if not articles:
                        st.warning("No se encontraron artículos válidos.")
                    else:
                        df = pd.DataFrame(articles)
                        st.success(f"✅ {len(df)} artículos encontrados para '{tema}'")

                        # Mostrar artículos
                        for _, r in df.iterrows():
                            with st.expander(f"📄 {r['titulo']} ({r.get('año', 'N/A')})"):
                                st.markdown(f"**Autores:** {r.get('autores', 'Desconocido')}")
                                st.markdown(f"**Fuente:** {r.get('fuente', 'N/A')}")
                                resumen = r.get('resumen', 'Sin resumen disponible')
                                st.markdown(f"**Resumen:** {resumen[:500]}...")
                                if r.get("url"):
                                    st.markdown(f"[🔗 Ver artículo]({r['url']})", unsafe_allow_html=True)

                        # Estadísticas
                        mostrar_estadistica(df)

                        # Resumen y PDF
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
                st.error(f"❌ Error al buscar artículos: {e}")
