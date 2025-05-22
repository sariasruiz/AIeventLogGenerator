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
    with open(ed_schema_path, "r", encoding="utf-8") as file:
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

    # Sidebar
    with st.sidebar:
        # Botón de cerrar sesión
        if AUTH_REQUIRED and st.button("Cerrar sesión"):
            logout()
        
        footer()

    # Título y descripción
    title()
    st.markdown("## Arquitectura del Sistema")

    # Diagrama de arquitectura
    base_path = Path(__file__).parent.parent
    st.image(base_path / "static/images/architecture.svg", width=1250)

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
                
    - **Usuario inicia interacción** a través de la interfaz de usuario.
    - **(Puntos del diagrama: 1).** El AI Agent inicia contextualización del problema, realizando 5 preguntas metodológicas para la construcción de un log de eventos y 2 técnicas en concepto de validación y visualización de datos.
    - **(Puntos del diagrama: 2 y 3)**. Finalizada la contextualización del problema, el AI Agent resumen informe de necesidad del usuario y llama a la herramienta (“AI Tool”) “search_and_generate_sql”.
    - **(Puntos del diagrama: 4, 5, 6, 7 y 8)**. La herramienta inicia la técnica RAG, generando un vector de representación semántica “embedding” del informe de necesidad del usuario. Realiza una búsqueda semántica del conocimiento sobre la base de datos relacional almacenada en Qdrant. Si la información recuperada supera score de 0.5, se incorpora al flujo de trabajo como contexto relevante recuperado.
    - **(Puntos del diagrama: 9)**. Con el contexto relevante recuperado se inicia el bloque de generación de script SQL.
    - **(Puntos del diagrama: 10, 11 y 12)**. Se crea un prompt con el informe de necesidad del usuario, el contexto relevante recuperado y unas instrucciones para la generación de un log de eventos. Se invoca una instancia del LLM razonador “o4-mini” para que genere la primera versión del Script SQL.
    - **(Puntos del diagrama: 13, 14, 15 y 16)**. Se crea un segundo prompt, con todo el contenido del primero, añadiendo el script SQL generado e instrucciones de revisión de sintaxis, búsqueda de errores y mejoras de legibilidad. Se invoca una segunda instancia del LLM razonador “o4-mini” para que genere la versión final del Script SQL.
    - **(Puntos del diagrama: 17 y 18)**. El Script SQL mejorado se envía directamente al usuario concluyendo el flujo de trabajo del AI Agent conversacional.
    
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

# Llamada a la página de arquitectura
app() 