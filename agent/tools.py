###############################################
# tools.py
###############################################
# Notas:
# En `tools.py` los prompts NO se han llevado a prompts_templates.py,
# Se ha preferido tener centralizada toda la funcionalidad en el módulo de tools para facilitar seguimiento.
# También se han añadido puntos de control para capturar datos del comportamiento,
# se activan si DATA_EXPERIMENT en .env está a 'YES'.
# los logs de experimento se guardan en el fichero '<uuid>.json' en el directorio 'output'.

import logging
import json
import os
from typing import List

from dotenv import load_dotenv

from langchain.tools import tool
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from agent.retriever import QdrantRetriever
from agent.utils.logging_config import setup_logging
from agent.experiment_log import Experiment, is_experiment_enabled

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)


# Tool: Busca en Qdrant el contexto relevante (RAG) y genera SQL en una sola llamada
@tool(
    name_or_callable="search_and_generate_sql",
    # Devuelve el resultado directamente, sin usar el LLM del agente (El agente debe terminar ahí.)
    return_direct=True,
    description="""
    Basándose en un informe de la necesidad del usuario como entrada,
    esta herramienta:
    Primero, buscará el contexto relevante en la base de datos de datos corporativa.
    Posteriormente generará directamente un script SQL
    siguiendo un formato adaptado para la generación de logs de eventos.
    """
)
def search_and_generate_sql(user_needs: str) -> dict:
    """Recupera contexto del esquema + genera SQL en una sola llamada."""
    
    ##################################################
    # Punto 1 control de experimento: Inicio Tool.
    experiment = None
    if is_experiment_enabled():
        try:
            experiment = Experiment(user_needs)
        except Exception as e:
            logger.warning(f"Fallo en experiment.add_retriever_start: {e}")
    ##################################################

    # Configuración LLM
    provider = os.getenv("SQL_LLM_PROVIDER", "OPENAI").upper()
    model = os.getenv("SQL_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("SQL_LLM_TEMPERATURE", 0))

    if provider == "OPENAI":
        llm = ChatOpenAI(model=model, temperature=temperature)
    else:
        return {"error": f"Proveedor LLM todavía no soportado: {provider}"}

    ##################################################
    # Punto 2 control de experimento: Inicio recuperación RAG
    if experiment:
        try:
            experiment.add_retriever_start()
        except Exception as e:
            logger.warning(f"Fallo en experiment.add_retriever_start: {e}")
    ##################################################

    # Recuperar contexto de Qdrant (RAG)
    retriever = QdrantRetriever()
    # Se capturan resultados que pasan el score, los resultados en bruto y el score límite que aplicó
    results_score_pass, results_score_raw, score_limit = retriever.search(query=user_needs)

    ##################################################
    # Punto 3 control de experimento: Fin recuperación RAG
    
    if experiment:
        try:
            experiment.add_retriever_finish(
                result_pass=results_score_pass,  # Resultado que pasa el filtro.
                result_raw=results_score_raw,  # Scores limite para pasar el filtro.
                score_limit=score_limit,
                embedding_model=retriever.embedding_model_name, # no confundir con .embedding_model
                embedding_tokens=retriever.get_embedding_tokens()
            )
        except Exception as e:
            logger.warning(f"Fallo en experiment.add_retriever_finish: {e}")
    ##################################################

    # Si no hay resultados que pasen el filtro, devolvemos error.
    if not results_score_pass:
        return {
            "error": "No se encontró información relevante en el esquema.",
            "context": "",
            "prompt": "",
            "sql_script": ""
        }

    # El resultado de la técnica RAG, es nuestra parte del prompt de contexto de esquema.
    # Se hace este paso, redundante por si en el futuro se cree interesante
    # aplicar aquí algún tipo de preprocesado de los resultados de RAG.
    schema_context = results_score_pass

    # Parte del prompt con el resumen de las necesidades del usuario.
    # Este resumen de necesidad, es generado por el LLM del agente, después
    # de lanzarle las preguntas metodológicas al usuario.
    user_summary = f"Consulta del usuario: {user_needs}"

    # Prompt para la generación de un Log de Eventos Hospitalarios (SQL)
    # Aquí describe la parte del prompt que regula el formato del script SQL a generar.
    script_sql_format = (
        """
        # Tu tarea principal es: Generación de un **Log de Eventos Hospitalarios** en formato de script SQL,
          siguiendo las reglas siguientes:

        ## 0. Reglas básicas:
        - Tu único conocimiento sobre la base de datos corporativaes el contexto del esquema proporcionado.
        - Contesta únicamente con el código SQL sin ningún comentario adicional.
        - No incluyas comentarios de cortesía o despedida. Eres un generador de código.
        - Asegura no generar campos o tablas inexistentes en el contexto de la base de datos proporcionado.
        - Si el usuario no tiene claro el objetivo, y pide algo parecido a "dame un log de eventos de los pacientes que han llegado a Urgencias",
          intenta generar un log de eventos con todos los `id` posibles en el contexto recuperado, infiere eventos que dispongan de 'timestamps' en sus tablas y añade como atributos todas las columnas restantes de las mismas.
        
        ## 1. Identificadores únicos. (obligatorio)
        - Incorpora los identificadores únicos al principio del script manteniendo su nombre oiriginal.
        - Estos identificadores permiten reconocer de forma inequívoca cada instancia del proceso (p. ej., un paciente o una estancia).

        ## 2. Marca temporal. (obligatorio)
        - Registra el momento exacto en que sucede cada evento.
        - Formato fecha `timestamp` (`YYYY-MM-DD HH:MM:SS`).
        - Mapea la columna original a **`timestamps`**.

        ## 3. Nombre del evento. (obligatorio)
        - Describe la actividad realizada (p. ej., *Admisión del paciente*, *Alta del paciente*, *Inicio de intervención*).
        - Mapea la columna original a **`activity`**.
        - Si el usuario repite el nombre de un evento, añade sufijo numérico para diferenciarlos.
        - Si el usuario no te da un valor exacto para su nombre, usa el nombre de la actividad que mejor se ajuste.
        - Es necesario que el evento solicitado presente una marca temporal, ya sea una columna: "Fecha Hora", "Fecha"+"Hora".
        - Algunos eventos especiales pueden requerir una reconstrucción atípica, 
          que involucran cálculos uniones varias tablas, dichos casos se especifican en el contexto de la base de datos.

        ## 4. Atributos adicionales *(opcionales)*
        - Añade columnas con la información complementaria relevante para el análisis (p. ej., *nivel de triaje*, *código diagnóstico*, *Laboratorio*, ...).
        - Mantén los nombres originales de las columnas de atributos siempre que sea posible.

        ## 5. Reglas de formato del script SQL
        - Ajusta el dialecto al motor de base de datos.
        - Utiliza **CTEs** (`WITH`) para separar los distintos tipos de evento (p. ej., admisiones, altas, medicaciones).
        - Combina todas las CTEs con **`UNION ALL`**.
        - Especifica el esquema de la base de datos en el `FROM`.
        - Orden de columnas en cada CTE y en el `UNION ALL` final:
            1. Columnas con los identificadores únicos
            2. `timestamps`
            3. `activity`
            4. Columnas de Atributos adicionales.
        - Si un atributo se repite en varios eventos, usa **una sola** columna.
        - Si algún atributo tiene secuencia, NO limites al primer elemento, a no ser que lo especifique el usuario. (ojo con el uso de JOIN o LEFT JOIN si es necesario repetir eventos para mantener la secuencia.)
        - Cuando un atributo no aplique a un evento, rellénalo con `NULL`. 
        - Usa los nombres originales de las columnas salvo los mapeos indicados de `timestamps` y `activity`, o los mapeos que indique el usuario.
        - Concluye siempre con **`ORDER BY timestamps ASC`** sin ';' al final del script.
       
        ## 6. Ejemplo de output del script SQL.

        | <columna id1> | <columna id2> | timestamps          | activity   | <columna atributo1> | <columna atributo2> | … |,
        |---------------|---------------|---------------------|------------|---------------------|---------------------|---|,
        | 12345         | 21231         | 2025-04-18T08:30:00 | Llegada    | 2                   | NULL                | … |,
        | 12345         | 21231         | 2025-04-19T09:25:00 | Alta       | NULL                | B34.9               | … |,

        """
    )

    # Se genera el prompt final a partir de las 3 partes anteriores.
    # Este prompt contiene necesidad del usuario, contexto de la base de datos y formato del script SQL.
    prompt_sql_generator = f"""
            Eres un experto en SQL hospitalario. Genera un log de eventos en formato SQL según las reglas siguientes.

            # Necesidades del usuario:
            {user_summary}

            # Contexto del esquema:
            {schema_context}

            # Reglas del formato SQL:
            {script_sql_format}
            """

    # Se intenta lanzar la primera invocación del LLM para generar el script SQL.
    try:
        
        ##################################################
        # Punto 4 control de experimento: Inicio 1a generación SQL

        if experiment:
            try:
                experiment.add_sql_generator_start()
            except Exception as e:
                logger.warning(f"Fallo en experiment.add_sql_generator_start: {e}")
        ##################################################
        
        # 1a Generación del Script SQL con modelo LLM
        response = llm.invoke(prompt_sql_generator)

        #logger.info(json.dumps(response.response_metadata, indent=2, ensure_ascii=False))
        sql_script = response.content.strip()
        
        ##################################################
        # Punto 5 control de experimento: Fin 1a generación SQL
        if experiment:
            try:
                experiment.add_sql_generator_finish(
                    prompt=prompt_sql_generator, 
                    sql_script=sql_script, 
                    metadata_llm=response.response_metadata
                    )
            except Exception as e:
                logger.warning(f"Fallo en experiment.add_sql_generator_finish: {e}")

        # Se genera el prompt para la 2a generación del Script SQL,
        # que tiene como objetivo, mejorar el resultado de la primera generación.
        prompt_enhance_sql = f"""
            Eres un experto en SQL hospitalario. Revisa el script SQL generado y realiza las correcciones necesarias.

            # Bloque de contexto de necesidades del usuario, conocimientos de la base de datos corporativa y formato del script SQL:
            #################################
            {prompt_sql_generator}

            # Script SQL generado para satisfacer las necesidades del usuario:
            #################################
            {sql_script}

            # Objetivo
            #################################
            Revisa en busca de inconsistencias y errores en el script SQL generado en base a:
            - las necesidades del usuario.
            - conocimiento de la base de datos corporativa.
            - formato del script SQL.
            - mantener la coherencia de los tipos de datos originales en todo el script.

            Explica al usuario:
            - Comenta los bloques de eventos según el contexto de la base de datos.
            - Comenta los campos individuales que lo componen según contexto de la base de datos. (unidad, significado, etc.)
            - Indica los campos que *NO* se han podido encontrar al principio del script (con: `--` no: `/**/`).
            
            # Output:
            #################################
            - Script SQL corregido y mejorado.
            """
        
        # Se lanza la 2a Generación del Script SQL para la búsqueda de errores, inconsistencias y mejoras de formato.
        if experiment:
            try:
                experiment.add_sql_enhanced_start()
            except Exception as e:
                logger.warning(f"Fallo en experiment.add_sql_enhanced_start: {e}")
        
        response_enhanced = llm.invoke(prompt_enhance_sql)
        sql_script_enhanced = response_enhanced.content.strip()
        #logger.info(json.dumps(response_enhanced.response_metadata, indent=2, ensure_ascii=False))
        
        if experiment:
            try:
                experiment.add_sql_enhanced_finish(
                    prompt=prompt_enhance_sql,
                    sql_script=sql_script_enhanced,
                    metadata_llm=response_enhanced.response_metadata
                    )
                experiment.finish()

            except Exception as e:
                logger.warning(f"Fallo en experiment.add_sql_enhanced_finish: {e}")
        
        # Se devuelve el script SQL mejorado.
        return  f"```sql\n{sql_script_enhanced}\n```"

    # Si hay algún error, se captura y se devuelve un error de fallo en la generación del script SQL.
    except Exception as exc:
        logger.error(f"Fallo en la generación del script SQL: {exc}")
        if experiment:
            experiment.finish()
        return {
            "error": str(exc),
            "context": schema_context,
            "prompt": prompt_sql_generator,
            "sql_script": "[ERROR]",
        }