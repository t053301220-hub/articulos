import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from collections import Counter
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib import colors
import io
from supabase import create_client, Client
import json

# Configuración de la página
st.set_page_config(
    page_title="Buscador Científico",
    page_icon="📚",
    layout="wide"
)

# Inicializar Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)

supabase = init_supabase()

# CSS personalizado
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 1rem;
        color: #666;
    }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">🔬 Buscador de Artículos Científicos</h1>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar para parámetros de búsqueda
with st.sidebar:
    st.header("📋 Parámetros de Búsqueda")
    
    tema = st.text_input(
        "📚 Tema de investigación",
        placeholder="Ej: machine learning, diabetes, climate change",
        key="tema_input"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input(
            "📅 Desde",
            datetime(2020, 1, 1),
            key="fecha_inicio"
        )
    with col2:
        fecha_fin = st.date_input(
            "📅 Hasta",
            datetime.now(),
            key="fecha_fin"
        )
    
    idioma = st.selectbox(
        "🌐 Idioma",
        ["es,en", "es", "en"],
        format_func=lambda x: {
            "es,en": "Español e Inglés",
            "es": "Solo Español",
            "en": "Solo Inglés"
        }[x],
        key="idioma_select"
    )
    
    st.markdown("---")
    buscar_btn = st.button("🔍 Realizar Búsqueda", use_container_width=True, type="primary")
    
    st.markdown("---")
    st.subheader("📜 Historial de Búsquedas")
    if st.button("Ver Historial", use_container_width=True):
        st.session_state['mostrar_historial'] = True

# Función para guardar búsqueda en Supabase
def guardar_busqueda(tema, fecha_inicio, fecha_fin, idioma, total_resultados):
    try:
        data = {
            "tema": tema,
            "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
            "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
            "idioma": idioma,
            "total_resultados": total_resultados,
            "fecha_busqueda": datetime.now().isoformat()
        }
        result = supabase.table("busquedas").insert(data).execute()
        return result
    except Exception as e:
        st.error(f"Error al guardar en base de datos: {str(e)}")
        return None

# Función para obtener historial
def obtener_historial():
    try:
        result = supabase.table("busquedas").select("*").order("fecha_busqueda", desc=True).limit(10).execute()
        return result.data
    except Exception as e:
        st.error(f"Error al obtener historial: {str(e)}")
        return []

# Función para realizar la búsqueda
def buscar_articulos(tema, fecha_inicio, fecha_fin, idioma):
    url = "https://eriks20252.app.n8n.cloud/webhook/busqueda-cientifica"
    
    payload = {
        "tema": tema,
        "fechaInicio": fecha_inicio.strftime("%Y-%m-%d"),
        "fechaFin": fecha_fin.strftime("%Y-%m-%d"),
        "idioma": idioma
    }
    
    with st.spinner("🔄 Buscando artículos científicos..."):
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            st.error("⏱️ La búsqueda tardó demasiado. Intenta con un rango de fechas más pequeño.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error al conectar con el servidor: {str(e)}")
            return None

# Función para crear PDF mejorado
def crear_pdf(resultados, tema, stats):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                           topMargin=0.75*inch, bottomMargin=0.75*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.grey,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    
    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['BodyText'],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=4
    )
    
    # Portada
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph("📚 REPORTE DE BÚSQUEDA CIENTÍFICA", title_style))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Tema: {tema}", subtitle_style))
    story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Estadísticas resumen
    story.append(Paragraph("📊 RESUMEN ESTADÍSTICO", heading_style))
    
    stats_data = [
        ["Total de Artículos", str(stats['total'])],
        ["Rango de Años", f"{stats['año_min']} - {stats['año_max']}"],
        ["Autores Únicos", str(stats['autores_unicos'])],
        ["Fuentes", ", ".join(stats['fuentes'])]
    ]
    
    stats_table = Table(stats_data, colWidths=[2.5*inch, 4*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e6f2ff')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    story.append(stats_table)
    story.append(PageBreak())
    
    # Artículos
    story.append(Paragraph("📄 ARTÍCULOS ENCONTRADOS", heading_style))
    story.append(Spacer(1, 0.2*inch))
    
    for idx, art in enumerate(resultados, 1):
        # Título del artículo
        story.append(Paragraph(f"<b>{idx}. {art.get('titulo', 'Sin título')}</b>", body_style))
        
        # Información básica
        info_lines = []
        if art.get('autores') and art['autores'] != 'No especificado':
            info_lines.append(f"<b>Autores:</b> {art['autores'][:200]}...")
        info_lines.append(f"<b>Año:</b> {art.get('año', 'N/A')}")
        if art.get('venue'):
            info_lines.append(f"<b>Publicado en:</b> {art['venue']}")
        info_lines.append(f"<b>Fuente:</b> {art.get('fuente', 'N/A')}")
        
        for line in info_lines:
            story.append(Paragraph(line, small_style))
        
        # DOI y URL
        if art.get('doi'):
            story.append(Paragraph(f"<b>DOI:</b> {art['doi']}", small_style))
        if art.get('url'):
            story.append(Paragraph(f"<b>URL:</b> <link href='{art['url']}'>{art['url'][:80]}...</link>", small_style))
        
        # Resumen
        if art.get('resumen') and art['resumen'] != 'Resumen no disponible':
            resumen_text = art['resumen'][:500] + "..." if len(art['resumen']) > 500 else art['resumen']
            story.append(Paragraph(f"<b>Resumen:</b> {resumen_text}", body_style))
        
        # Objetivo y Metodología
        if art.get('objetivo') and art['objetivo'] != 'No especificado':
            story.append(Paragraph(f"<b>Objetivo:</b> {art['objetivo'][:300]}", body_style))
        
        if art.get('metodologia') and art['metodologia'] != 'No especificada':
            story.append(Paragraph(f"<b>Metodología:</b> {art['metodologia'][:300]}", body_style))
        
        # Palabras clave
        if art.get('palabras_clave') and art['palabras_clave'] != 'No registradas':
            story.append(Paragraph(f"<b>Palabras clave:</b> {art['palabras_clave'][:200]}", small_style))
        
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph("_" * 100, small_style))
        story.append(Spacer(1, 0.15*inch))
        
        # Nueva página cada 3 artículos
        if idx % 3 == 0 and idx < len(resultados):
            story.append(PageBreak())
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# Función para calcular estadísticas
def calcular_estadisticas(resultados):
    df = pd.DataFrame(resultados)
    
    # Limpiar años
    df['año_num'] = pd.to_numeric(df['año'], errors='coerce')
    df = df.dropna(subset=['año_num'])
    
    # Extraer todos los autores
    todos_autores = []
    for autores in df['autores']:
        if autores and autores != 'No especificado':
            todos_autores.extend([a.strip() for a in autores.split(',')])
    
    stats = {
        'total': len(resultados),
        'año_min': int(df['año_num'].min()) if not df.empty else 0,
        'año_max': int(df['año_num'].max()) if not df.empty else 0,
        'autores_unicos': len(set(todos_autores)),
        'fuentes': df['fuente'].unique().tolist() if 'fuente' in df.columns else []
    }
    
    return stats, df, todos_autores

# Mostrar historial si se solicitó
if st.session_state.get('mostrar_historial', False):
    st.subheader("📜 Historial de Búsquedas Recientes")
    historial = obtener_historial()
    
    if historial:
        df_historial = pd.DataFrame(historial)
        df_historial['fecha_busqueda'] = pd.to_datetime(df_historial['fecha_busqueda']).dt.strftime('%d/%m/%Y %H:%M')
        st.dataframe(
            df_historial[['tema', 'fecha_inicio', 'fecha_fin', 'idioma', 'total_resultados', 'fecha_busqueda']],
            use_container_width=True
        )
    else:
        st.info("No hay búsquedas en el historial.")
    
    if st.button("Cerrar Historial"):
        st.session_state['mostrar_historial'] = False
        st.rerun()

# Realizar búsqueda
if buscar_btn:
    if not tema:
        st.warning("⚠️ Por favor ingresa un tema de investigación.")
    elif fecha_inicio > fecha_fin:
        st.error("❌ La fecha de inicio debe ser anterior a la fecha fin.")
    else:
        resultados = buscar_articulos(tema, fecha_inicio, fecha_fin, idioma)
        
        if resultados and len(resultados) > 0:
            st.success(f"✅ Se encontraron {len(resultados)} artículos")
            
            # Guardar en Supabase
            guardar_busqueda(tema, fecha_inicio, fecha_fin, idioma, len(resultados))
            
            # Guardar en session state
            st.session_state['resultados'] = resultados
            st.session_state['tema_busqueda'] = tema
            
        elif resultados is not None:
            st.warning("⚠️ No se encontraron artículos con los criterios especificados.")
        # Si resultados es None, ya se mostró el error en buscar_articulos()

# Mostrar resultados si existen
if 'resultados' in st.session_state and st.session_state['resultados']:
    resultados = st.session_state['resultados']
    tema_busqueda = st.session_state.get('tema_busqueda', 'Búsqueda')
    
    # Calcular estadísticas
    stats, df, todos_autores = calcular_estadisticas(resultados)
    
    # Métricas principales
    st.subheader("📊 Estadísticas Descriptivas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats['total']}</div>
            <div class="stat-label">Artículos Total</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats['año_max'] - stats['año_min'] + 1}</div>
            <div class="stat-label">Años Cubiertos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats['autores_unicos']}</div>
            <div class="stat-label">Autores Únicos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(stats['fuentes'])}</div>
            <div class="stat-label">Fuentes</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráficos estadísticos
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Por Año", "👥 Autores Frecuentes", "📚 Por Fuente", "📄 Artículos"])
    
    with tab1:
        st.subheader("Publicaciones por Año")
        publicaciones_por_año = df['año_num'].value_counts().sort_index()
        
        fig_años = px.bar(
            x=publicaciones_por_año.index,
            y=publicaciones_por_año.values,
            labels={'x': 'Año', 'y': 'Número de Publicaciones'},
            title=f'Distribución Temporal de Publicaciones - {tema_busqueda}'
        )
        fig_años.update_traces(marker_color='#1f77b4')
        fig_años.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_años, use_container_width=True)
        
        # Estadísticas adicionales por año
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Año con más publicaciones", 
                     publicaciones_por_año.idxmax(),
                     f"{publicaciones_por_año.max()} artículos")
        with col2:
            promedio = publicaciones_por_año.mean()
            st.metric("Promedio por año", f"{promedio:.1f}")
    
    with tab2:
        st.subheader("Autores Más Frecuentes")
        contador_autores = Counter(todos_autores)
        top_autores = contador_autores.most_common(15)
        
        if top_autores:
            df_autores = pd.DataFrame(top_autores, columns=['Autor', 'Publicaciones'])
            
            fig_autores = px.bar(
                df_autores,
                x='Publicaciones',
                y='Autor',
                orientation='h',
                title='Top 15 Autores con Más Publicaciones'
            )
            fig_autores.update_traces(marker_color='#2ca02c')
            fig_autores.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_autores, use_container_width=True)
            
            st.dataframe(df_autores, use_container_width=True)
        else:
            st.info("No hay suficientes datos de autores para mostrar.")
    
    with tab3:
        st.subheader("Distribución por Fuente")
        fuentes_count = df['fuente'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pie = px.pie(
                values=fuentes_count.values,
                names=fuentes_count.index,
                title='Porcentaje por Fuente'
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            fig_bar_fuente = px.bar(
                x=fuentes_count.index,
                y=fuentes_count.values,
                labels={'x': 'Fuente', 'y': 'Cantidad'},
                title='Artículos por Fuente'
            )
            fig_bar_fuente.update_traces(marker_color='#ff7f0e')
            fig_bar_fuente.update_layout(height=400)
            st.plotly_chart(fig_bar_fuente, use_container_width=True)
    
    with tab4:
        st.subheader("Lista de Artículos Encontrados")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            años_disponibles = sorted(df['año_num'].unique())
            año_filtro = st.selectbox("Filtrar por año:", ["Todos"] + [int(a) for a in años_disponibles])
        
        with col2:
            fuente_filtro = st.selectbox("Filtrar por fuente:", ["Todas"] + stats['fuentes'])
        
        with col3:
            orden = st.selectbox("Ordenar por:", ["Más recientes", "Más antiguos", "Título"])
        
        # Aplicar filtros
        df_filtrado = df.copy()
        if año_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado['año_num'] == año_filtro]
        if fuente_filtro != "Todas":
            df_filtrado = df_filtrado[df_filtrado['fuente'] == fuente_filtro]
        
        # Ordenar
        if orden == "Más recientes":
            df_filtrado = df_filtrado.sort_values('año_num', ascending=False)
        elif orden == "Más antiguos":
            df_filtrado = df_filtrado.sort_values('año_num', ascending=True)
        else:
            df_filtrado = df_filtrado.sort_values('titulo')
        
        # Mostrar artículos
        st.write(f"**Mostrando {len(df_filtrado)} de {len(df)} artículos**")
        
        for idx, row in df_filtrado.iterrows():
            with st.expander(f"**{row['titulo']}** ({row['año']})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Autores:** {row['autores']}")
                    st.markdown(f"**Año:** {row['año']}")
                    if row.get('venue'):
                        st.markdown(f"**Revista/Conferencia:** {row['venue']}")
                    st.markdown(f"**Fuente:** {row['fuente']}")
                    
                    if row.get('resumen') and row['resumen'] != 'Resumen no disponible':
                        st.markdown("**Resumen:**")
                        st.write(row['resumen'][:500] + "..." if len(row['resumen']) > 500 else row['resumen'])
                
                with col2:
                    if row.get('doi'):
                        st.markdown(f"**DOI:** `{row['doi']}`")
                    if row.get('url'):
                        st.markdown(f"[🔗 Ver artículo completo]({row['url']})")
                    
                    if row.get('palabras_clave') and row['palabras_clave'] != 'No registradas':
                        st.markdown(f"**Palabras clave:** {row['palabras_clave'][:150]}")
                
                # Mostrar objetivo y metodología si están disponibles
                if row.get('objetivo') and row['objetivo'] != 'No especificado':
                    st.markdown(f"**🎯 Objetivo:** {row['objetivo']}")
                
                if row.get('metodologia') and row['metodologia'] != 'No especificada':
                    st.markdown(f"**🔬 Metodología:** {row['metodologia']}")
    
    # Botón de descarga
    st.markdown("---")
    st.subheader("📥 Descargar Resultados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Descargar como CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📊 Descargar CSV",
            data=csv,
            file_name=f"busqueda_{tema_busqueda}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Descargar como PDF
        pdf_buffer = crear_pdf(resultados, tema_busqueda, stats)
        st.download_button(
            label="📄 Descargar PDF",
            data=pdf_buffer,
            file_name=f"reporte_{tema_busqueda}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>🔬 Buscador Científico | Fuentes: CORE & CrossRef | Desarrollado con Streamlit</p>
    </div>
""", unsafe_allow_html=True)
