###############################################
# style.py
###############################################

import streamlit as st
from project.project import __version__, __author__, __description__, __url__, __year__, __email__, __university__

def page_config(layout="centered"):
    """
    Configura la página.
    layout: "centered" o "wide"
    """

    st.set_page_config(
        page_title=f"Process Mining: AI Event Log Generator v{__version__}",
        page_icon="🤖",
        layout=layout,
        initial_sidebar_state="collapsed"
    )

def title():
    """
    Configura el título de la página.
    """

    st.title("🤖 Chatbot AI Event Log Generator")
    st.markdown("""
    Chatbot impulsado por un Agente de IA mediante LLM y técnicas RAG (Generación Aumentada por Recuperación).\n
    Genera scripts SQL aptos para la construcción de logs de eventos a partir del conocimiento 
    obtenido de la base de datos de su centro hospitalario.\n\n
    """)

def how_get_access():
    """
    Instrucciones para obtener acceso al chatbot.
    """

    with st.expander("¿Cómo conseguir acceso al chatbot?"):
        st.write("""
        1. Envíe un correo electrónico a sergio.arias@uoc.edu con el asunto "Acceso al chatbot".
        2. Es indispensable que el correo electrónico pertenezca al dominio uoc.edu.
        """)

def footer():
    """
    Configura el footer de la página.
    """
    
    st.markdown(f"""

    <div>
        <br><br>
        v{__version__}  | <strong>{__author__}</strong>   |  {__year__}  |  {__university__} <br>
        <strong>{__description__}</strong> <br>
        <a href="{__url__}" target="_blank">
        <img src="https://img.shields.io/badge/Repositorio-GitHub-black?logo=github" alt="Repositorio GitHub">
        </a>
    </div>
    """, unsafe_allow_html=True)