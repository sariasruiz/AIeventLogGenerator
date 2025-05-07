import pandas as pd
import json
from pathlib import Path
import os
import plotly.express as px
from typing import List, Dict, Tuple

def get_fields_to_include() -> Tuple[List[str], List[str], Dict[str, str]]:
    """
    Devuelve los campos de interés para el cálculo de métricas.
    FIELDS_TO_INCLUDE: Versión extendida.
    FIELDS_TO_INCLUDE_REDUCED: Versión reducida, para resumenes.
    FIELDS_TO_INCLUDE_REDUCED_USER_FRIENDLY: Versión reducida, con nombres amigables.

    Devuelve tupa con las listas de valores y el diccionario de nombres amigables.
    ¡¡Ojo!! que el tercer elemento de devuelto es un diccionario.
    """
    # Campos de interés para cálculo de métricas.
    FIELDS_TO_INCLUDE = [
            # Identificación y fecha
            "id",
            "datetime",
            
            # Modelos LLM
            "llm_model_retriever_embedding",
            "llm_model_sql_generator",
            "llm_model_sql_generator_enhanced",
            
            # Tiempos
            "time_in_seconds_total",
            "time_in_seconds_retriever",
            "time_in_seconds_sql_generation",
            "time_in_seconds_sql_generation_enhanced",
            
            # Tokens
            "tokens_total_retriever_embedding",
            "tokens_total_sql_generation",
            "tokens_prompt_sql_generation",
            "tokens_completion_sql_generation",
            "tokens_total_sql_generation_enhanced",
            "tokens_prompt_sql_generation_enhanced",
            "tokens_completion_sql_generation_enhanced",
            "tokens_total_tool",
            
            # Costos
            "total_cost_retriever_embedding_in_dollars",
            "total_cost_sql_generation_in_dollars",
            "total_cost_sql_generation_enhanced_in_dollars",
            "total_cost_tool_in_dollars",
            
            # Métricas del retriever
            "retriever_score_limit",
            "retriever_score_count_pass",
        ]

    # Campos de interés versión reducida para resumen
    FIELDS_TO_INCLUDE_REDUCED = [
            # Identificación y fecha
            "id",
            "datetime",
            
            # Tiempos
            "time_in_seconds_total",
            "time_in_seconds_retriever",
            "time_in_seconds_sql_generation",
            "time_in_seconds_sql_generation_enhanced",
            
            # Tokens
            "tokens_total_tool",
            "tokens_total_retriever_embedding",
            "tokens_total_sql_generation",
            "tokens_total_sql_generation_enhanced",
            
            # Costos
            'total_cost_tool_in_dollars',
            "total_cost_retriever_embedding_in_dollars",
            "total_cost_sql_generation_in_dollars",
            "total_cost_sql_generation_enhanced_in_dollars",
            "retriever_score_count_pass"
        ]

    # Mapeo de nombres de columnas a nombres amigables para el usuario.
    FIELDS_TO_INCLUDE_REDUCED_USER_FRIENDLY = {
            "id": "ID",
            "datetime": "Fecha y Hora",
            "time_in_seconds_total": "Tiempo Total (s)",
            "time_in_seconds_retriever": "Tiempo Retriever (s)",
            "time_in_seconds_sql_generation": "Tiempo SQL Generator (s)",
            "time_in_seconds_sql_generation_enhanced": "Tiempo SQL Generator Enhanced (s)",
            "tokens_total_tool": "Tokens Totales",
            "tokens_total_retriever_embedding": "Tokens Retriever",
            "tokens_total_sql_generation": "Tokens SQL Generator",
            "tokens_total_sql_generation_enhanced": "Tokens SQL Generator Enhanced",
            "total_cost_tool_in_dollars": "Coste Total ($)",
            "total_cost_retriever_embedding_in_dollars": "Coste Retriever ($)",
            "total_cost_sql_generation_in_dollars": "Coste SQL Generator ($)",
            "total_cost_sql_generation_enhanced_in_dollars": "Coste SQL Generator Enhanced ($)",
            "retriever_score_count_pass": "Vectores Recuperados"
        }
    
    return FIELDS_TO_INCLUDE, FIELDS_TO_INCLUDE_REDUCED, FIELDS_TO_INCLUDE_REDUCED_USER_FRIENDLY

def get_output_dir() -> Path:
    """
    Apunta al directorio donde estan los `.json`
    de `experiment_log`
    """
    return Path(__file__).parent.parent.parent / "output"

def load_metrics_data() -> pd.DataFrame:
    """
    Carga los datos de métricas desde los archivos JSON en el directorio output.
    Solo procesa archivos que empiecen por 'TestToolAgent_'.
    Incluye solo los campos específicos definidos en la lista FIELDS_TO_INCLUDE.
    
    çRetorna un DataFrame con los datos seleccionados.
    """
    
    # Obtener la ruta base del proyecto (un nivel arriba de ui)
    metrics_dir = get_output_dir()
    
    # Lista para almacenar todos los datos
    all_data = []
    
    # Verificar si el directorio existe
    if not metrics_dir.exists():
        raise ValueError(f"El directorio de métricas no existe: {metrics_dir}")
    
    # Procesar cada archivo JSON que empiece por TestToolAgent_
    for file in metrics_dir.glob("TestToolAgent_*.json"):
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                # Crear un diccionario solo con las métricas que interesen
                filtered_data = {k: data.get(k) for k in get_fields_to_include()[0]}
                all_data.append(filtered_data)
        except Exception as e:
            print(f"Error procesando archivo {file}: {str(e)}")
    
    if not all_data:
        raise ValueError("No se encontraron archivos JSON de métricas de TestToolAgent para procesar")
    
    # Convertir a DataFrame
    df = pd.DataFrame(all_data)
    
    return df

############################################################
# Sección de métricas
###############################################

# Creamos el bloque de cálculo de métricas.
# El return se hace en la mayoría de casos como diccionario para facilitar la lectura y recuperación de los datos.
def calculate_total_experiments(df: pd.DataFrame) -> int:
    """
    Calcula el número total de experimentos realizados.
    """
    return len(df)

def calculate_time_metrics(df: pd.DataFrame) -> dict:
    """
    Calcula las métricas de tiempo promedio.
    """
    return {
        'total_time_avg': df['time_in_seconds_total'].mean(),
        'retriever_time_avg': df['time_in_seconds_retriever'].mean(),
        'sql_generation_time_avg': df['time_in_seconds_sql_generation'].mean(),
        'sql_generation_enhanced_time_avg': df['time_in_seconds_sql_generation_enhanced'].mean()
    }

def calculate_token_metrics(df: pd.DataFrame) -> dict:
    """
    Calcula las métricas de tokens promedio.
    """
    return {
        'total_tokens_avg': df['tokens_total_tool'].mean(),
        'retriever_tokens_avg': df['tokens_total_retriever_embedding'].mean(),
        'sql_generation_tokens_avg': df['tokens_total_sql_generation'].mean(),
        'sql_generation_enhanced_tokens_avg': df['tokens_total_sql_generation_enhanced'].mean()
    }

def calculate_cost_metrics(df: pd.DataFrame) -> dict:
    """
    Calcula las métricas de coste promedio.
    """
    return {
        'total_cost_avg': df['total_cost_tool_in_dollars'].mean(),
        'retriever_cost_avg': df['total_cost_retriever_embedding_in_dollars'].mean(),
        'sql_generation_cost_avg': df['total_cost_sql_generation_in_dollars'].mean(),
        'sql_generation_enhanced_cost_avg': df['total_cost_sql_generation_enhanced_in_dollars'].mean()
    }

def calculate_retriever_metrics(df: pd.DataFrame) -> dict:
    """
    Calcula las métricas del retriever.
    """
    return {
        'avg_retrieved_vectors': df['retriever_score_count_pass'].mean()
    }

############################################################
# Sección de gráficos
#########################################################
# PAra los gráficos devolvemos tupla con la figura del total y la figura de los componentes.
def create_time_boxplots(df: pd.DataFrame) -> tuple:
    """
    Crea los boxplots para los tiempos.
    Se retorna figura total y figura componentes.
    """
    # Boxplot del tiempo total
    fig_total = px.box(
        df, 
        y='time_in_seconds_total',
        title='Tiempo Total de Ejecución',
        color_discrete_sequence=['#FF4B4B']
    )
    fig_total.update_layout(
        yaxis_title='Tiempo (segundos)',
        showlegend=False,
        height=400
    )

    # Boxplot de por componentes
    df_components = df.melt(
        value_vars=[
            'time_in_seconds_retriever',
            'time_in_seconds_sql_generation',
            'time_in_seconds_sql_generation_enhanced'
        ],
        var_name='Componente',
        value_name='Tiempo'
    )
    
    # Mapeo de nombres de columnas a nombres amigables
    component_names = {
        'time_in_seconds_retriever': 'Retriever (RAG)',
        'time_in_seconds_sql_generation': 'SQL Generator',
        'time_in_seconds_sql_generation_enhanced': 'SQL Generator Enhanced'
    }
    
    df_components['Componente'] = df_components['Componente'].map(component_names)
    
    fig_components = px.box(
        df_components,
        x='Componente',
        y='Tiempo',
        title='Tiempos por Componente',
        color_discrete_sequence=['#FF4B4B']
    )
    fig_components.update_layout(
        yaxis_title='Tiempo (segundos)',
        xaxis_title='',
        showlegend=False,
        height=400
    )

    return fig_total, fig_components

def create_token_boxplots(df: pd.DataFrame) -> tuple:
    """
    Crea los boxplots para los tokens.
    Se retorna figura total y figura componentes.
    """
    # Boxplot de tokens totales
    fig_total = px.box(
        df,
        y='tokens_total_tool',
        title='Tokens Totales',
        color_discrete_sequence=['#FF4B4B']
    )
    fig_total.update_layout(
        yaxis_title='Número de Tokens',
        showlegend=False,
        height=400
    )

    # Boxplot de los componentes
    df_components = df.melt(
        value_vars=[
            'tokens_total_retriever_embedding',
            'tokens_total_sql_generation',
            'tokens_total_sql_generation_enhanced'
        ],
        var_name='Componente',
        value_name='Tokens'
    )
    
    # Mapeo de nombres de columnas a nombres amigables
    component_names = {
        'tokens_total_retriever_embedding': 'Retriever (RAG)',
        'tokens_total_sql_generation': 'SQL Generator',
        'tokens_total_sql_generation_enhanced': 'SQL Generator Enhanced'
    }
    
    df_components['Componente'] = df_components['Componente'].map(component_names)
    
    fig_components = px.box(
        df_components,
        x='Componente',
        y='Tokens',
        title='Tokens por Componente',
        color_discrete_sequence=['#FF4B4B']
    )
    fig_components.update_layout(
        yaxis_title='Número de Tokens',
        xaxis_title='',
        showlegend=False,
        height=400
    )

    return fig_total, fig_components

def create_cost_boxplots(df: pd.DataFrame) -> tuple:
    """
    Crea los boxplots para los costes.
    Se retorna figura total y figura componentes.
    """
    # Boxplot del coste total
    fig_total = px.box(
        df,
        y='total_cost_tool_in_dollars',
        title='Coste Total',
        color_discrete_sequence=['#FF4B4B']
    )
    fig_total.update_layout(
        yaxis_title='Coste ($)',
        showlegend=False,
        height=400
    )

    # Boxplot de los componentes
    df_components = df.melt(
        value_vars=[
            'total_cost_retriever_embedding_in_dollars',
            'total_cost_sql_generation_in_dollars',
            'total_cost_sql_generation_enhanced_in_dollars'
        ],
        var_name='Componente',
        value_name='Coste'
    )

    # Mapeo de nombres de columnas a nombres amigables
    component_names = {
        'total_cost_retriever_embedding_in_dollars': 'Retriever (RAG)',
        'total_cost_sql_generation_in_dollars': 'SQL Generator',
        'total_cost_sql_generation_enhanced_in_dollars': 'SQL Generator Enhanced'
    }
    
    df_components['Componente'] = df_components['Componente'].map(component_names)

    fig_components = px.box(
        df_components,
        x='Componente',
        y='Coste',
        title='Costes por Componente en USD',
        color_discrete_sequence=['#FF4B4B']
    )
    fig_components.update_layout(
        yaxis_title='Coste (USD)',
        xaxis_title='',
        showlegend=False,
        height=400
    )

    return fig_total, fig_components
