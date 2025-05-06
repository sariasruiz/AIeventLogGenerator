###############################################
# app_architecture.py
###############################################

import streamlit as st
import json
from ui.utils.style import footer, page_config, title
from ui.auth.auth_decorators import require_auth
import os
from ui.auth.auth import logout
from dotenv import load_dotenv
from pathlib import Path
# Cargar variables de entorno
load_dotenv()

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED","YES").upper()=="YES"

def load_ed_schema():
    """
    Cargamos el archivo ed_schema.json y lo formateamos para que sea más legible.
    """
    # Path del archivo
    base_path = Path(__file__).parent.parent.parent
    ed_schema_path = base_path / "knowledge/ed_schema.json"
    with open(ed_schema_path, "r") as file:
        json_ed_schema = json.load(file)
    
    # Formateo de legibilidad del json
    json_ed_schema_formatted = json.dumps(
        json_ed_schema, 
        indent=2, # Indentación de 2 espacios
        ensure_ascii=False
        )
    
    return json_ed_schema_formatted

@require_auth
def app():
    """
    Página que muestra la arquitectura del sistema.
    """

    # Configurar la página
    page_config(layout="wide")

    # Sidebar con metadatos del chatbot
    with st.sidebar:
        # Botón de cerrar sesión
        if AUTH_REQUIRED and st.button("Cerrar sesión"):
            logout()
        
        footer()

    # Título y descripción
    title()
    st.markdown("## Arquitectura del Sistema")

    # Diagrama de arquitectura
    st.image("static/images/architecture.svg", width=1250)

    # Tecnologías utilizadas
    st.markdown("""
    ### Tecnologías Utilizadas

    - **Framework Frontend**: Streamlit
    - **Autenticación**: AWS Cognito
    - **LLM base AI Agent**: OpenAI GPT-4o-mini
    - **LLM Razonador Generador de Script SQL**: OpenAI o4-mini
    - **LLM Razonador Generador de Script SQL Mejorado**: OpenAI o4-mini
    - **Framework de Agentes**: LangChain
    - **Base de Datos Vectorial**: Qdrant
    - **Base de Datos SQL**: PostgreSQL
    - **Infraestructura**: AWS Lightsail (Instancia NGINX+Ubuntu)
    """)

    # Flujo de datos
    st.markdown(f"""
    ### Pipeline Principal

    - El usuario inicia sesión a través de Cognito.
    - El usuario verificado interactúa con el chat. **(Punto 1 del diagrama)**
    - El agente LLM realiza 5 preguntas metodológicas para contextualizar el log de eventos. **(Punto 1 del diagrama)**
    - El agente LLM llama a la herramienta `search_and_generate_sql`. **(Punto 2 del diagrama)**
    - Se inicia la técnica RAG: Se construye un vector de embeddings para realizar la búsqueda semántica en Qdrant y recuperar el contenido relevante de la base de datos vectorial. **(Punto 3, 4, 5, 6, 7 y 8 del diagrama.)**
    - El contenido recuperado se pasa a un modelo LLM razonador junto a la necesidad del usuario y a unas reglas de formato del Script. **(Puntos 9, 10 y 11 del diagrama)**
    - El modelo LLM Razonador devuelve una primera versión del Script SQL. **(Punto 12 del diagrama)**.
    - Se vuelve a invocar un segundo modelo LLM Razonador, que recibe como prompt lo que recibió el primer LLM Razonador, más el script SQL generado y unas instrucciones de búsqueda de errores, inconsistencias y puntos de mejora.  **(Puntos 13 y 14 del diagrama)**
    - Se Genera el script SQL mejorado y se devuelve de manera directa al usuario. **(Puntos 15, 16, 17 y 18 del diagrama).**
    - Finaliza la acción con el agente.
    
    ### Pipeline Secundario

    - Antes de poner en marcha la app *AI Event Log Generator*, se ejecuta un pipeline secundario de: "Almacenamiento de Conocimiento en Base de Datos Vectorial".
    - Primero se construye un archivo `.json` estandarizado con características técnicas de la estructura y documentación en lenguaje natural sobre el módulo, tablas y campos presentes en cualquier base de datos realacional."
    - La generación del `<prefijo>_schema.json` con la información estructural es libre (se puede seguir un proceso manual, semiautomático o automático), únicamente hay que respetar de manera estricta la estructura del archivo.
    - Mediante el script `load_schema.py` procesa el archivo `.json` y ejecuta el módulo `loader.py` del agente. 
    - Esta ejecución, genera embeddings para cada una de las tablas del archivo.
    - Al almacenar 1 vector por tabla, cuando el usuario pregunta por un campo aislado, el recuperador consigue el contexto completo inmediato de ese campo.
    - Los vectores son almacenados en la base de datos vectorial Qdrant con un nombre identificativo (colección).
    - Este proceso se realiza una única vez.
                
    ### Privacidad y Seguridad de los datos
                
    - El AI agent, **no almacena ningún dato clínico o identificativo del paciente, ni accede de manera directa a la base de datos**.
    - El AI agent, **funciona principalmente con datos técnicos y descriptivos** de la propia estructura de la base de datos. 
    - La estructura se enriquece con los posibles valores que puede tomar un determinado campo:
                
        - **Valores mínimos y máximos:** (Ejemplo, min: 0 max: 100), en tipos de datos numéricos.

        - **Valores más frecuentes:** (Ejemplo, "F", "M" para el género).
                
    ### Estructura del `ed_schema.json` estandarizado:
    """)

    st.code(load_ed_schema(), language="json")

    footer()

# Ejecutamos la página:
app() 