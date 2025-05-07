import streamlit as st
import os
import pandas as pd
from ui.utils.style import footer, page_config, title
# Importamos las métricas de interés
from ui.utils.metrics import (
    get_fields_to_include,
    load_metrics_data,
    calculate_total_experiments,
    calculate_time_metrics,
    calculate_token_metrics,
    calculate_cost_metrics,
    calculate_retriever_metrics,
    create_time_boxplots,
    create_token_boxplots,
    create_cost_boxplots
)
from ui.auth.auth import logout
from ui.auth.auth_decorators import require_auth
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED","YES").upper()=="YES"

@require_auth
def app():
    """
    Página que muestra las métricas de la Tool de Generación de Logs de Eventos de todos los usuarios.
    """

    # Configurar la página
    page_config(layout="wide")

    # Barra lateral standard.
    with st.sidebar:
        # Botón de cerrar sesión
        if AUTH_REQUIRED and st.button("Cerrar sesión"):
            logout()
        
        footer()

    # Título y descripción
    title()
    
    try:
        # Cargar los datos
        df = load_metrics_data()
        
        # Verificar si hay datos
        if df.empty:
            st.warning("No hay datos disponibles para mostrar. De momento no existen métricas que calcular.")
            return
        
        # Calcular métricas principales
        total_experiments = calculate_total_experiments(df)
        time_metrics = calculate_time_metrics(df)
        token_metrics = calculate_token_metrics(df)
        cost_metrics = calculate_cost_metrics(df)
        retriever_metrics = calculate_retriever_metrics(df)
        
        # Subtitulo
        st.markdown("## Métricas de AI Tool: Generación de Logs de Eventos")

        # Mostrar métricas principales en la parte superior
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="Número de llamadas",value=total_experiments)
        
        with col2:
            st.metric(
                label="Promedio seg. de respuesta.",
                value=f"{time_metrics['total_time_avg']:.1f} seg")
        
        with col3:
            st.metric(
                label="Promedio Tokens consumidos",
                value=f"{token_metrics['total_tokens_avg']:.1f}")
        
        with col4:
            st.metric(
                label="Promedio Coste en USD",
                value=f"${cost_metrics['total_cost_avg']:.2f}")
        
        with col5:
            st.metric(
                label="Promedio Vectores Recuperados.",
                value=f"{retriever_metrics['avg_retrieved_vectors']:.1f}")
        
        # Secciones para los boxplots
        tab1, tab2, tab3, tab4 = st.tabs(["Tiempos", "Tokens", "Costes", "Casos Detallados"])
        
        # Tiempos
        with tab1:
            st.subheader("Análisis de Tiempos")
            fig_time_total, fig_time_components = create_time_boxplots(df)
            col1, col2 = st.columns([1, 2])
            with col1:
                st.plotly_chart(fig_time_total, use_container_width=True)
            with col2:
                st.plotly_chart(fig_time_components, use_container_width=True)
        
        # Tokens
        with tab2:
            st.subheader("Análisis de Tokens")
            fig_token_total, fig_token_components = create_token_boxplots(df)
            col1, col2 = st.columns([1, 2])
            with col1:
                st.plotly_chart(fig_token_total, use_container_width=True)
            with col2:
                st.plotly_chart(fig_token_components, use_container_width=True)        
        
        # Costes
        with tab3:
            st.subheader("Análisis de Costes")
            fig_cost_total, fig_cost_components = create_cost_boxplots(df)
            col1, col2 = st.columns([1, 2])
            with col1:
                st.plotly_chart(fig_cost_total, use_container_width=True)
            with col2:
                st.plotly_chart(fig_cost_components, use_container_width=True)
        
        # Casos Detallados
        with tab4:
            st.subheader("Casos Detallados")
            
            # Preparar datos para mostrar
            detailed_df = df.copy()
            
            # DEfinimos las columnas resumen del dataframe
            # Que se definían en la Tupla de la función get_fields_to_include()[1]            
            # Seleccionamos las columnas relevantes
            detailed_df = detailed_df[get_fields_to_include()[1]]
            
            # Definimos nuevos nombres para las columnas y mejorar visualización.
            # Recuperamos el diccionario de mapeo de nombres amigables.
            column_names = get_fields_to_include()[2]
            
            # Renombrar las columnas
            detailed_df = detailed_df.rename(columns=column_names)
            
            # Formateo de fechayhora
            detailed_df['Fecha y Hora'] = pd.to_datetime(detailed_df['Fecha y Hora']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Mostramos el Datagrame
            st.dataframe(detailed_df, use_container_width=True)
            
            # Botón de exportación
            csv = detailed_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar CSV",
                data=csv,
                file_name="metricas_detalladas.csv",
                mime="text/csv"
            )
        
    except Exception as e:
        st.error(f"Error durante el proceso de carga de los datos: {str(e)}")
    

# Llamada a la página de métricas
app()
