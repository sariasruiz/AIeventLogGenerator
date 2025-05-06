###############################################
# auth_decorators.py
###############################################

import streamlit as st
from functools import wraps
from ui.auth.auth import AuthManager, login_page
import logging
from agent.utils.logging_config import setup_logging
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED","YES").upper()=="YES" 

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)


def require_auth(func):
    """
    Decorador que verifica si el usuario está autenticado.
    Si no está autenticado, muestra un mensaje de error y detiene la ejecución.
    Simplemente se usa para verificar si el usuario está autenticado antes de acceder a una sección.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if AUTH_REQUIRED:
            if "auth_manager" not in st.session_state:
                st.session_state.auth_manager = AuthManager()

            if not st.session_state.auth_manager.check_session():
                login_page()
                st.stop()
        return func(*args, **kwargs)
    return wrapper