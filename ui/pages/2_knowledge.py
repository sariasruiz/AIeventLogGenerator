###############################################
# docc_knowledge.py
###############################################

import streamlit as st
import json
from pathlib import Path
from ui.utils.style import footer, page_config, title
from ui.auth.auth_decorators import require_auth
import os
from ui.auth.auth import logout
from dotenv import load_dotenv


# Cargar variables de entorno
load_dotenv()

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED","YES").upper()=="YES"

# Función para cargar JSON
def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error al cargar el conocimiento disponible en {file_path}: {str(e)}")
        return None

@require_auth
def app():
    """
    Página que muestra la documentación de la base de datos.
    """

    # Configurar la página
    page_config(layout="wide")

    # Sidebar 
    with st.sidebar:
        if AUTH_REQUIRED and st.button("Cerrar sesión"):
            logout()
            
        footer()

    # Título y descripción
    title()
    st.markdown("## Conocimiento disponible")
    st.markdown("Traducción de fuente oficial: [MIMIC-IV](https://mimic.mit.edu/docs/iv/)")

    # Cargar módulos
    base_dir = Path(__file__).parent.parent.parent
    modules_path = base_dir / "knowledge/documentation/modules.json"
    modules_data = load_json(modules_path)
    if not modules_data:
        st.error("No se pudo cargar la información de los módulos")
        return

    # Cargar tablas del módulo ED
    ed_tables_path = base_dir / "knowledge/documentation/module_ed"
    ed_tables = {
        # Capturamos el nombre del archivo sin la extensión .stem (Módulo librería Path)
        json_file.stem: 
        # Cargamos cada archivo ".json" que esté en el directorio
        load_json(json_file) for json_file in ed_tables_path.glob("*.json")
        }

    # Crear tabs manualmente
    tab0a, tab0b, tab1, tab2, tab3 = st.tabs(["modelo relacional", "prompt experimento","module_ed", "module_hosp", "module_icu"])
    
    # Modelo relacional de MIMIC-IV
    with tab0a:
        # Modelo relacional de MIMIC-IV
        st.markdown("## Modelo relacional de MIMIC-IV")
        base_path = Path(__file__).parent.parent
        st.image(base_path / "static/images/mimic_iv_model.svg", width=500)
        st.markdown("*Figura 1. Modelo relacional de MIMIC-IV. 2025. Fuente propia.*")

        # Información de los módulos cargados en este experimento
        st.markdown("## Conocimiento cargado en este experimento")
        st.markdown("Módulo: ED (Urgencias)")

        base_path = Path(__file__).parent.parent
        st.image(base_path / "static/images/mimic_iv_model_ed.svg", width=1000)
        st.markdown("*Figura 2. Modelo relacional de MIMIC-IV: Módulo ED. 2025. Fuente propia.*")

    # Prompt experimento
    with tab0b:
        st.markdown("## Prompt utilizado en el experimento.")

        st.markdown("""
        Si desea utilizar el prompt que se testeó en el experimento, **siga cuidadosamente las siguientes instrucciones:**
                 
        - Inicie una conversación con el AI Agent.
        - Cuando el asistente le pregunte si desea responder a las preguntas de una en una o todas a la vez, **responda todas las preguntas a la vez.**
        - A continuación copie y pegue el **prompt** proporcionado a continuación.

        **Nota:** El prompt se diseñó para intentar reconstruir el log de eventos [MIMICEL](https://physionet.org/content/mimicel-ed/2.1.0/).  
        """)

        st.markdown("""
        ```text
        Objetivo: Generar un log de eventos, que involucre todo el módulo de urgencias, para trazar los eventos generados en el servicio de extremo a extremo.

        Grupo de pacientes: Toda la población en general.

        Identificadores únicos: Quiero poder captura el id del paciente, la id de estancia en urgencias, y en el caso de que dispongan, la id de estancia hospitalaria, y la id de intervención quirúrgica.

        Eventos a capturar:
        - Llegada del paciente de urgencias (con el nombre de 'Entrada a Urgencias (ED)').
        - Alta del paciente (con el nombre de 'Salida de Urgencias (ED)').
        - Triaje del paciente (con el nombre 'Triaje en Urgencias (ED)').
        - Toma de constantes vitales mientras está en urgencias (con el nombre de 'Toma de Constantes Vitales').
        - La entrevista de conciliación de medicamento (con el nombre 'Conciliación de Medicamentos').
        - La dispensación de medicamentos (bajo el nombre de 'Dispensación de Medicamentos').
        - Las pruebas de laboratorio (bajo el nombre de 'Pruebas de Laboratorio')
        - Y por último el evento de pruebas radiológicas. (bajo el nombre de 'Pruebas Radiológicas')

        Como atributos en los siguientes eventos:
        - De la llegada del paciente: El medio de llegada del paciente, el género, la edad y si hay más campos disponibles captúralos.
        - Del alta del paciente: Me gustaría registrar el motivo de alta, toda la secuencia de códigos de diagnósticos, descripciones y la versiones de codificación utilizada.
        - Del triaje: Me gustaría obtener el nivel de triaje, todas las tomas de constantes vitales realizadas en triaje, y campos de texto libre si existen.
        - De la toma de constantes vitales, me gustaría al igual que en Triaje, todas las tomas de constantes vitales.
        - Durante la conciliación de medicamentos, no tengo claro que campos podemos obtener, incorpora todos los campos posibles como atributo.
        - Durante la dispensación de medicamentos, me ocurre lo mismo, no tengo claro que podemos obtener, introduce todos los campos posibles como atributo.
        - De las pruebas de laboratorio, me gustaría capturar el nombre de tipo de prueba.
        - Del evento de pruebas radiológicas, me gustaría capturar el nombre de tipo de prueba.

        Validación de datos:
        - Las estancias deberían ser: 'llegada a Urgencias (ED)' < 'Alta de Urgencias (ED)'
        - Además se debe cumplir que: 
        1. 'Toma de Constantes Vitales' <= 'Alta de Urgencias (ED)'
        2. 'Dispensación de Medicamentos' <= 'Alta de Urgencias (ED)'
        3. 'Conciliación de Medicamentos' <= 'Alta de Urgencias (ED)'

        Orden de datos:
        Quiero ordenar el resultado por orden de id paciente ascendente y por marca de tiempo del evento ascendente.
        ```
        """)

    # Módulo ED
    with tab1:
        # Mostrar descripción del módulo ED
        ed_module = modules_data["modules"][1]
        if ed_module:
            st.markdown(ed_module["description"]["spanish"])
            st.write("")

        # Crear secciones para cada tabla
        table_tabs = st.tabs([table_name for table_name in ed_tables.keys()])
        
        for table_tab, (table_name, table_data) in zip(table_tabs, ed_tables.items()):
            with table_tab:
                if "table" in table_data:
                    if "name" in table_data["table"]:
                        st.subheader(table_data["table"]["name"])
                        st.write("")
                    if "definition" in table_data["table"]:
                        st.markdown("**Descripción:**")
                        st.write(table_data["table"]["definition"]["spanish"])
                        st.write("")
                    if "purpose" in table_data["table"]:
                        st.markdown("**Propósito:**")
                        st.write(table_data["table"]["purpose"]["spanish"])
                        st.write("")
                
                for field in table_data.get("fields", []):
                    with st.expander(field["name"]):
                        st.write(field["description"]["spanish"])

    # Módulo HOSP
    with tab2:
        # Mostrar descripción del módulo HOSP
        hosp_module = modules_data["modules"][0]
        if hosp_module:
            st.warning("Documentación del módulo HOSP no se ha cargado para este experimento.")
            st.write(hosp_module["description"]["spanish"])
    
    # Módulo ICU
    with tab3:
        # Mostrar descripción del módulo ICU
        icu_module = modules_data["modules"][2]
        if icu_module:
            st.warning("Documentación del módulo ICU no se ha cargado para este experimento.")
            st.write(icu_module["description"]["spanish"])

    footer()

# Llamada a la página de conocimiento
app() 