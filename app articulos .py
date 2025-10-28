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

# =============================
# CONFIGURACIÓN BASE
# =============================
st.set_page_config(page_title="Asistente de Búsqueda Científica", layout="wide")
st.title("🔬 Asistente de Búsqueda Científica")

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
    """Muestra estadísticas descriptivas en Streamlit."""
    st.subheader("📊 Estadísticas descriptivas")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total artículos", len(df))
    c2.metric("Fuentes únicas", df["fuente"].nunique())
    c3.metric("Años distintos", df["año"].nunique())

    df["año"] = pd.to_numeric(df["año"], errors="coerce")

    st.markdown("#### Distribución de publicaciones por año")
    st.plotly_chart(px.histogram(df, x="año", nbins=15, title="Publicaciones por año"), use_container_width=True)

    if df["año"].notna().any():
        año_mas = int(df["año"].mode().iloc[0])
        total = (df["año"] == año_mas).sum()
        st.info(f"📅 Año con más publicaciones: {año_mas} ({total} artículos)")

# =============================
# INTERFAZ PRINCIPAL
# =============================

with st.form("busqueda_form"):
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

            if isinstance(data, list):
                articles = [a.get("json", a) for a in data]
            else:
                articles = []

            if not articles:
                st.warning("⚠️ No se encontraron artículos para ese tema.")
            else:
                df = pd.DataFrame(articles)
                st.success(f"✅ {len(df)} artículos encontrados para '{tema}'")

                # Mostrar artículos
                for _, r in df.iterrows():
                    with st.expander(f"📄 {r['titulo']} ({r['año']})"):
                        st.markdown(f"**Autores:** {r['autores']}")
                        st.markdown(f"**Fuente:** {r['fuente']}")
                        st.markdown(f"**Resumen:** {r['resumen'][:500]}...")
                        if r.get("url"):
                            st.markdown(f"[🔗 Ver artículo completo]({r['url']})", unsafe_allow_html=True)

                # Estadísticas
                mostrar_estadistica(df)

                # PDF
                resumen = {
                    "Artículos encontrados": len(df),
                    "Fuentes únicas": df["fuente"].nunique(),
                    "Años distintos": df["año"].nunique()
                }
                pdf = generar_pdf(df, tema, resumen)
                st.download_button(
                    "📥 Descargar PDF de resultados",
                    data=pdf,
                    file_name=f"busqueda_{tema}.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"❌ Error al conectar con el servicio: {e}")
