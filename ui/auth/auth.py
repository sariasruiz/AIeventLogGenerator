################################################################################
# auth.py
#
# Versión FAKE de autenticación para despliegue en local o entorno demo.
#
# Simula el comportamiento de logueo únicamente.
#
# Credenciales en self.credentials con usuario:demo y contraseña:demo
# de manera intencional para uso en pruebas local o demo.
# ¡¡¡ No usar en producción !!!
#
# Motivo: No se expone la clase AuthManager real para no exponer posibles
# vulnerabilidades en el proceso de autenticación de la demo de producción.
#
# Cada desarrollador debe implementar su propia clase de autenticación
# según sus necesidades y proveedores.
#
# NOTA: Esta clase la invoca auth_decorators.py
################################################################################

import streamlit as st
from ui.utils.style import footer, page_config, title

class AuthManager:
    """
    Clase ultra simplificada para autenticación.
    Solo valida credenciales fijas (demo/demo).
    Se crea para no exponer posibles vulnerabilidades en
    el proceso de autenticación real.
    """
    def __init__(self):
        self.credentials = {
            "demo": "demo"  # usuario: contraseña
        }

    def validate_credentials(self, username: str, password: str) -> bool:
        """
        Valida las credenciales sin modificar el estado.
        """
        if not username or not password:
            return False, "Por favor, debe ingresar usuario y contraseña."

        if username in self.credentials and self.credentials[username] == password:
            return True, "Login Exitoso. Bienvenid@"
        
        return False, "Usuario o contraseña incorrectos."

    def set_session(self, username: str):
        """
        Establece el estado de la sesión.
        """
        st.session_state.authenticated = True
        st.session_state.username = username

    def clear_session(self):
        """
        Limpia el estado de la sesión.
        """
        if "authenticated" in st.session_state:
            del st.session_state.authenticated
        if "username" in st.session_state:
            del st.session_state.username

    def check_session(self) -> bool:
        """
        Verifica si hay una sesión activa.
        Consistente con la verificación que hace el decorador.
        """
        return st.session_state.get("authenticated", False)

def login_page():
    """
    Página de login simplificada.
    """
    page_config()
    title()
    
    with st.form("login_form"):
        st.subheader("Iniciar Sesión")
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Iniciar Sesión")
        
        if submit:
            # Usar la instancia que ya está en session_state
            if "auth_manager" not in st.session_state:
                st.session_state.auth_manager = AuthManager()
            
            auth = st.session_state.auth_manager
            success, message = auth.validate_credentials(username, password)
            
            if success:
                auth.set_session(username)
                st.success(message)
                st.rerun()
            else:
                st.error(message)
    
    footer() 