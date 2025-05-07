import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

def get_output_dir() -> Path:
    """
    Apunta al directorio donde estan los `.json`
    de `experiment_log`
    """
    return Path(__file__).parent.parent.parent / "output"

def load_generations() -> List[Dict]:
    """
    Se extraen los logs de Scripts SQL generados en la carpeta `output`.
    Ene esta caso devolvemos lista de diccionarios.
    """
    # Apuntamos al directorio `output`
    output_dir = get_output_dir()

    # Si no existe, devolvemos lista vacía
    if not output_dir.exists():
        print("Directorio no existe")
        return []

    # Lista para guardar todas las generaciones
    scripts_sql_list = []

    # Buscar todos los archivos que empiezan por TestToolAgent_
    for file in output_dir.glob("TestToolAgent_*.json"):
        try:
            # Leer el archivo JSON
            with open(file, 'r') as f:
                data = json.load(f)
                
                # Verificar que tiene los campos necesarios
                if "datetime" in data and "prompt_user_needs" in data and "sql_script_enhanced" in data:
                    scripts_sql_list.append(data)
                    
        except Exception as e:
            st.error(f"Error en load_generations() al leer el archivo: {file}: {e}")
            return []
    
    # Devolvemos la lista de diccionarios.
    return scripts_sql_list

def format_generation(gen: Dict) -> Dict:
    """
    La lista de diccionarios devuelta por `load_generations()` debe ser formateada.
    **Selector**: sirve para identificar la generación de script SQL (`YYYY-MM-DD HH:MM:SS - ID`)
    **prompt_user_needs**: es el resumen de la necesidad del usuario.
    **sql_script_enhanced**: es el script SQL mejorado generado.
    **filename**: es el nombre del archivo, con el que se guarda la descarga del script SQL.
    """
    # Extraemos el campo `datetime` del log y lo formateamos.
    date = datetime.strptime(gen['datetime'], '%Y-%m-%d %H:%M:%S')

    # Devolvemos el diccionario con los campos seleccionados.
    return {
        'selector': f"{date.strftime('%Y-%m-%d %H:%M:%S')} - {gen['id']}",
        'prompt_user_needs': gen['prompt_user_needs'],
        'sql_script_enhanced': gen['sql_script_enhanced'],
        'filename': f"SQL_{gen['id']}.sql"
    } 