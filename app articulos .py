# =============================
# app.py — Asistente de Búsqueda Científica con guardado en Supabase
# =============================
import streamlit as st
import requests
import pandas as pd
from supabase import create_client, Client
import datetime
import plotly.express as px
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

# === Conexión a Supabase ===
url = st.secrets["supabase"]["supabase_url"]
key = st.secrets["supabase"]["supabase_key"]
supabase: Client = create_client(url, key)

# === URL de tu webhook activo en n8n ===
WEBHOOK_URL = "https://eriks20252.app.n8n.cloud/webhook/busqueda-cientifica"

# =============================
# FUNCIONES AUXILIARES
# =============================

def guardar_en_supabase(df):
    """Guarda los artículos en la tabla 'articulos' de Supabase."""
    try:
        data_list = df.to_dict(orient="records")
        for articulo in data_list:
            articulo["fecha_busqueda"] = datetime.datetime.utcnow().isoformat()
            supabase.table("articulos").insert(articulo).execute()
        st.success(f"🗃️ {len(data_list)} artículos guardados correctamente en Supabase.")
    except Exception as e:
        st.error(f"❌ Error al guardar en Supabase: {e}")

def generar_pdf(df, tema, resumen_estadistico):
    """Genera un PDF con resumen estadístico y artículos."""
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
        data.append([
            str(r.get("titulo", "")),
            str(r.get("autores", "")),
            str(r.get("año", "")),
            str(r.get("fuente", ""))
        ])
    table = Table(data, colWidths=[200, 150, 50, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    content.append(table)
    doc.build(content)
    buffer.seek(0)
    return buffer

def mostrar_estadistica(df):
    """Muestra estadísticas descriptivas visuales."""
    st.subheader("📊 Estadística descriptiva")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total artículos", len(df))
    c2.metric("Fuentes únicas", df["fuente"].nunique() if "fuente" in df else 0)
    c3.metric("Años distintos", df["año"].nunique() if "año" in df else 0)

    if "año" in df:
        df["año"] = pd.to_numeric(df["año"], errors="coerce")
        st.plotly_chart(px.histogram(df, x="año", nbins=15, title="📈 Publicaciones por año"), use_container_width=True)

    if "palabras_clave" in df:
        palabras = []
        for kw in df["palabras_clave"].dropna():
            palabras.extend([k.strip() for k in str(kw).split(",") if k.strip()])
        if palabras:
            top_kw = pd.Series(palabras).value_counts().head(10)
            st.plotly_chart(
                px.bar(x=top_kw.index, y=top_kw.values, title="🔑 Palabras clave más frecuentes"),
                use_container_width=True,
            )

# =============================
# INTERFAZ PRINCIPAL
# =============================
st.markdown("#### Ingresa los parámetros de búsqueda")

tema = st.text_input("📚 Tema de investigación")
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("📅 Fecha inicio", datetime.date(2020, 1, 1))
with col2:
    fecha_fin = st.date_input("📅 Fecha fin", datetime.date.today())
idioma = st.selectbox("🌐 Idioma", ["es,en", "es", "en"])

if st.button("🔍 Buscar artículos"):
    if not tema:
        st.warning("Por favor, escribe un tema para buscar.")
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
                    st.error(f"❌ Error del servidor ({res.status_code}) → {res.text}")
                else:
                    data = res.json()
                    if not data or not isinstance(data, list):
                        st.warning("No se encontraron artículos.")
                    else:
                        df = pd.DataFrame(data)
                        st.success(f"✅ {len(df)} artículos encontrados para '{tema}'")

                        # === GUARDAR EN SUPABASE ===
                        guardar_en_supabase(df)

                        # === MOSTRAR RESULTADOS ===
                        for _, r in df.iterrows():
                            titulo = r.get("titulo", "Sin título")
                            año = r.get("año", "N/A")
                            with st.expander(f"📄 {titulo} ({año})"):
                                st.markdown(f"**Autores:** {r.get('autores', 'No especificado')}")
                                st.markdown(f"**Fuente:** {r.get('fuente', 'Desconocida')}")
                                st.markdown(f"**Publicación / Venue:** {r.get('venue', 'No registrado')}")
                                st.markdown(f"**Objetivo:** {r.get('objetivo', 'No especificado')}")
                                st.markdown(f"**Metodología:** {r.get('metodologia', 'No especificada')}")
                                st.markdown(f"**Palabras clave:** {r.get('palabras_clave', 'No registradas')}")
                                resumen = r.get("resumen", "Sin resumen disponible")
                                st.markdown(f"**Resumen:** {resumen[:800]}...")
                                if r.get("url"):
                                    st.markdown(f"[🔗 Ver artículo completo]({r['url']})", unsafe_allow_html=True)

                        # === ESTADÍSTICAS ===
                        mostrar_estadistica(df)

                        # === PDF ===
                        resumen = {
                            "Artículos encontrados": len(df),
                            "Fuentes únicas": df["fuente"].nunique() if "fuente" in df else 0,
                            "Años distintos": df["año"].nunique() if "año" in df else 0,
                        }
                        pdf_buffer = generar_pdf(df, tema, resumen)
                        st.download_button(
                            label="📥 Descargar PDF de resultados",
                            data=pdf_buffer,
                            file_name=f"busqueda_{tema}.pdf",
                            mime="application/pdf",
                        )

            except Exception as e:
                st.error(f"❌ Error al buscar artículos: {e}")
