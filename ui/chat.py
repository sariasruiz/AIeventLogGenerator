###############################################
# chat.py
###############################################

import sys
from pathlib import Path

# Se añade la raáiz del pryecto al sys.path
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import streamlit as st
from ui.utils.style import footer, page_config, title
from agent.agent import Agent
from ui.auth.auth_decorators import require_auth
import os
from dotenv import load_dotenv
from ui.auth.auth import logout

# Cargar variables de entorno
load_dotenv()

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED","YES").upper()=="YES"

# Decorador para proteger contenido
@require_auth
def app():
    """
    Función principal que ejecuta el chatbot en el framework Streamlit.
    """

    # Se inicializa el agente y se guarda en sesión de streamlit
    if "agent" not in st.session_state:
        st.session_state.agent = Agent()

    # Se inicializa el historial de mensajes y se guarda en sesión de streamlit
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Configurar la página
    page_config()

    # Título
    title()

    # Obtener y mostrar el número de vectores
    try:
        collection_info = st.session_state.agent.retriever.client.get_collection(st.session_state.agent.retriever.collection)
        num_vectors = collection_info.points_count
        qdrant_status = True
    except Exception as e:
        #st.badge("no disponible", color="orange")
        qdrant_status = False
        st.error(f"Error en Qdrant, revisa que Qdrant esté activado o que la colección en .env esté creada.")

    # Sidebar con metadatos del chatbot
    with st.sidebar:
        # Botón de cerrar sesión
        if AUTH_REQUIRED and st.button("Cerrar sesión"):
            logout()

        st.header("Metadatos Chat AI Event Log Generator")
        
        # LLM Info
        st.subheader("AI Agent")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Proveedor:**")
            st.markdown(f"**Modelo:**")
            st.markdown(f"**Temperatura:**")
        with col2:
            st.badge(f"{st.session_state.agent.llm_provider}", color="green")
            st.badge(f"{st.session_state.agent.llm_model}", color="green")
            st.badge(f"{st.session_state.agent.llm_temperature}", color="green")

        st.subheader("Embeddings:")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Proveedor:**")
            st.markdown(f"**Modelo:**")
            st.markdown(f"**Colección:**")
            st.markdown(f"**Vectores:**")

        with col2:
            st.badge(f"{st.session_state.agent.retriever.embedding_provider}", color="orange")
            st.badge(f"{st.session_state.agent.retriever.embedding_model}", color="orange")
            st.badge(f"{st.session_state.agent.retriever.collection}", color="orange")
            # Obtener y mostrar el número de vectores si se pudo conectar a Qdrant
            if qdrant_status:
                st.badge(f"{num_vectors:,}", color="orange")
            else:
                st.badge("no disponible", color="orange")

        # LLM Info del generador de SQL
        # En .env
        st.subheader("LLM Razonador Generación SQL")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Proveedor:**")
            st.markdown(f"**Modelo:**") 
            st.markdown(f"**Temperatura:**")
        with col2:
            st.badge(f"{os.getenv('SQL_LLM_PROVIDER')}", color="blue")
            st.badge(f"{os.getenv('SQL_LLM_MODEL')}", color="blue")
            st.badge(f"{os.getenv('SQL_LLM_TEMPERATURE')}", color="blue")
        
        footer()

    # Mostrar historial de chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Si Qdrant está funcionando, se muestra la pantalla de chat
    if qdrant_status:
        st.warning(
            "¡Atención! La generación del script SQL puede demorar más de 2 minutos. Es una tarea compleja, por favor tenga paciencia.",
            icon=":material/warning:"
        )


        # Input del usuario
        if prompt := st.chat_input("Empieza a interactuar con la IA para generar tu log de eventos"):
            # Añadir mensaje del usuario
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Obtener respuesta
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    # Obtenemos respuesta pasando el prompt
                    response = st.session_state.agent.chat(prompt)

                    # Mostrar respuesta en interfaz
                    st.markdown(response)

                    # Añadir respuesta al historial
                    st.session_state.messages.append({"role": "assistant", "content": response})

        # Botón para limpiar la conversación
        if st.button("Limpiar conversación"):
            st.session_state.messages = []
            st.session_state.agent.clear()
            st.rerun()

if __name__ == "__main__":
    app()