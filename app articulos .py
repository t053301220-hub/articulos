# =============================
# app_articulos.py
# =============================
import streamlit as st
import requests
import pandas as pd
from supabase import create_client
import datetime

# Configuración
st.set_page_config(page_title="🔬 Asistente de Búsqueda Científica", layout="wide")
st.title("🔬 Asistente de Búsqueda Científica")

# --- CREDENCIALES (ya configuradas en Streamlit Cloud Settings -> Secrets)
SUPABASE_URL = st.secrets["supabase_url"]
SUPABASE_KEY = st.secrets["supabase_key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Webhook n8n
WEBHOOK_URL = "https://eriks20252.app.n8n.cloud/webhook/busqueda-cientifica"

# --- INTERFAZ ---
st.markdown("### Parámetros de búsqueda")
tema = st.text_input("📚 Tema de investigación")
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("📅 Desde", datetime.date(2020, 1, 1))
with col2:
    fecha_fin = st.date_input("📅 Hasta", datetime.date.today())
idioma = st.selectbox("🌐 Idioma", ["es", "en", "es,en"])

# --- EJECUCIÓN ---
if st.button("🔍 Buscar artículos"):
    if not tema:
        st.warning("Por favor ingresa un tema.")
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
                    if not data:
                        st.warning("No se encontraron artículos.")
                    else:
                        df = pd.DataFrame(data)
                        st.success(f"✅ {len(df)} artículos encontrados para '{tema}'")

                        # --- GUARDAR EN SUPABASE ---
                        fecha_busqueda = datetime.datetime.now().isoformat()
                        registros = []
                        for _, r in df.iterrows():
                            registro = {
                                "titulo": r.get("titulo", "Sin título"),
                                "autores": r.get("autores", "No especificado"),
                                "año": str(r.get("año", "N/A")),
                                "doi": r.get("doi", ""),
                                "url": r.get("url", ""),
                                "resumen": r.get("resumen", "No disponible"),
                                "fuente": r.get("fuente", ""),
                                "venue": r.get("venue", ""),
                                "objetivo": r.get("objetivo", "No especificado"),
                                "metodologia": r.get("metodologia", "No especificada"),
                                "palabras_clave": r.get("palabras_clave", "No registradas"),
                                "fecha_busqueda": fecha_busqueda
                            }
                            registros.append(registro)

                        try:
                            supabase.table("articulos").insert(registros).execute()
                            st.success("📦 Artículos guardados correctamente en Supabase.")
                        except Exception as e:
                            st.error(f"❌ Error al guardar en Supabase: {e}")

                        # --- MOSTRAR RESULTADOS ---
                        for _, r in df.iterrows():
                            with st.expander(f"📄 {r.get('titulo', 'Sin título')} ({r.get('año', 'N/A')})"):
                                st.markdown(f"**Autores:** {r.get('autores', 'No especificado')}")
                                st.markdown(f"**Fuente:** {r.get('fuente', 'Desconocida')}")
                                st.markdown(f"**Publicación / Venue:** {r.get('venue', 'No registrado')}")
                                st.markdown(f"**Objetivo:** {r.get('objetivo', 'No especificado')}")
                                st.markdown(f"**Metodología:** {r.get('metodologia', 'No especificada')}")
                                st.markdown(f"**Palabras clave:** {r.get('palabras_clave', 'No registradas')}")
                                resumen = r.get("resumen", "Sin resumen disponible")
                                st.markdown(f"**Resumen:** {resumen[:700]}...")
                                if r.get("url"):
                                    st.markdown(f"[🔗 Ver artículo]({r['url']})", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"❌ Error general: {e}")

