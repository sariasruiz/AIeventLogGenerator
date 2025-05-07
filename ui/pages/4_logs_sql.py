import streamlit as st
import os
from ui.utils.style import footer, page_config, title
from ui.auth.auth import logout
from ui.auth.auth_decorators import require_auth
from ui.utils.logs_sql import load_generations, format_generation
from dotenv import load_dotenv

# Configuración básica
load_dotenv()

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED","YES").upper()=="YES"

@require_auth
def app():
    """
    Página con resumen del prompt y la query SQL generada.
    para mejorar la trazabilidad de los experimentos.
    """
    # Configuración de la página
    page_config(layout="wide")
    

    # Barra lateral standard.
    with st.sidebar:
        # Botón de cerrar sesión
        if AUTH_REQUIRED and st.button("Cerrar sesión"):
            logout()
        
        footer()
    
    # Título y descripción
    title()
    
    # Cargar y formatear página de logs SQL
    try:
        # Cargar y formatear generaciones
        scripts_sql_list = [format_generation(gen) for gen in load_generations()]
        
        # Si no se encuentran experimentos, avisamos.
        if not scripts_sql_list:
            st.warning("No hay generaciones disponibles para mostrar.")
            return
        
        # Si no existe variable de estado, para la selección la creamos
        if 'selected_sql_script' not in st.session_state:
            st.session_state.selected_sql_script = scripts_sql_list[0]['selector']

        # Selector de script SQL
        selection_options = [script['selector'] for script in scripts_sql_list]
        try:
            # Captura el índice de la selección guardada en variables de estado
            index_selected = selection_options.index(st.session_state.selected_sql_script)
        except ValueError:
            # Si no existe, siempre índice 0
            index_selected = 0
        

        # Elemento de selección de script SQL
        st.session_state.selected_sql_script = st.selectbox(
            "Selecciona una generación de Scritp SQL",
            options=selection_options,
            index=index_selected
        )
        
        # Mostrar generación seleccionada
        for gen in scripts_sql_list:
            if gen['selector'] == st.session_state.selected_sql_script:
                selected_gen = gen
        
        # Mostrar resumen del prompt
        st.markdown("### Prompt")
        st.markdown(selected_gen['prompt_user_needs'])
        
        # Mostrar SQL con botón de descarga de streamlit
        st.markdown("### SQL Generada")
        st.markdown(f"```sql\n{selected_gen['sql_script_enhanced']}\n```")
        st.download_button(
            "Descargar script SQL",
            selected_gen['sql_script_enhanced'],
            file_name=selected_gen['filename'],
            mime="text/plain"
        )
            
    except FileNotFoundError:
        st.error("No se encontraron archivos de generación")
    except Exception as e:
        st.error(f"Error inesperado: {str(e)}")

# LLamada a la página de logs SQL
app()