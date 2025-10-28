import streamlit as st
import requests
import pandas as pd
from datetime import date
from supabase import create_client, Client
import os

# -----------------------------
# 🔧 CONFIGURACIÓN DE SUPABASE
# -----------------------------
# Tus credenciales deben estar configuradas en el panel de Streamlit Cloud:
# (en la sección "Secrets" -> "Edit secrets")
# Ejemplo:
# [supabase]
# url = "https://TU_URL.supabase.co"
# key = "TU_API_KEY"

url: str = st.secrets["supabase"]["url"]
key: str = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# -----------------------------
# 🎯 INTERFAZ DE BÚSQUEDA
# -----------------------------
st.title("🔍 Buscador de Literatura Científica")

tema = st.text_input("📚 Tema de investigación", placeholder="Ej. Inteligencia Artificial en Educación")

col1, col2, col3 = st.columns(3)
with col1:
    fecha_inicio = st.date_input("📅 Desde", date(2020, 1, 1))
with col2:
    fecha_fin = st.date_input("📅 Hasta", date.today())
with col3:
    idioma = st.selectbox("🌐 Idioma", ["es,en", "es", "en"], index=0)

buscar = st.button("🔎 Buscar artículos")

# -----------------------------
# 🚀 LLAMADA AL WORKFLOW N8N
# -----------------------------
if buscar:
    with st.spinner("Ejecutando búsqueda..."):
        webhook_url = "https://TU_INSTANCIA_N8N_URL/webhook/busqueda-cientifica"

        payload = {
            "tema": tema,
            "fechaInicio": str(fecha_inicio),
            "fechaFin": str(fecha_fin),
            "idioma": idioma
        }

        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            resultados = response.json()
        except Exception as e:
            st.error(f"❌ Error al conectar con el workflow: {e}")
            st.stop()

        if not resultados:
            st.warning("⚠️ No se encontraron artículos.")
        else:
            df = pd.DataFrame(resultados)
            st.success(f"✅ {len(df)} artículos encontrados")

            st.dataframe(df[["titulo", "autores", "año", "fuente", "objetivo", "metodologia"]])

            # Guardar automáticamente en Supabase
            with st.spinner("Guardando resultados en Supabase..."):
                try:
                    data_insert = df.to_dict(orient="records")
                    supabase.table("resultados_busqueda").insert(data_insert).execute()
                    st.success("📦 Resultados guardados correctamente en Supabase")
                except Exception as e:
                    st.warning(f"No se pudo guardar en Supabase: {e}")

            # Descargar CSV
            st.download_button(
                "⬇️ Descargar resultados en CSV",
                df.to_csv(index=False).encode("utf-8"),
                "resultados.csv",
                "text/csv"
            )
