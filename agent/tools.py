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
    Recibe como entrada el informe completo de necesidad del usuario 
    Con esta tool buscará el contexto relevante en la base de datos de datos corporativa.
    Posteriormente generará directamente un script SQL.
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
    temperature = float(os.getenv("SQL_LLM_TEMPERATURE", 1))

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
        # Tu tarea principal es: Generación de un **Log de Eventos Hospitalarios** en formato de script SQL compatible con el dialecto PostgreSQL,
          siguiendo las reglas siguientes:

        ## 0. Reglas básicas:
        - Tu único conocimiento es sobre la base de datos corporativa mediante el contexto del esquema proporcionado.
        - Contesta únicamente con el código SQL sin ningún comentario adicional.
        - No incluyas comentarios de cortesía o despedida. Eres un generador de código.
        - Asegura no generar campos o tablas inexistentes en el contexto de la base de datos proporcionado.
        - Si el usuario no tiene claro el objetivo, y pide algo parecido a "dame un log de eventos de los pacientes que han llegado a Urgencias",
          intenta generar un log de eventos con todos los `id` posibles en el contexto recuperado, infiere eventos que dispongan de 'timestamps' en sus tablas y añade como atributos todas las columnas restantes de las mismas.
        
        ## 1. Identificadores únicos. (obligatorio)
        - Incorpora los identificadores únicos al principio del script manteniendo su nombre original.
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
          que involucran cálculos o uniones de varias tablas, dichos casos se especifican en el contexto de la base de datos.

        ## 4. Atributos adicionales *(opcionales)*
        - Añade columnas con la información complementaria relevante para el análisis (p. ej., *nivel de triaje*, *código diagnóstico*, *Laboratorio*, ...).
        - Los atributos que se usan en algún evento, deben replicarse en el resto de eventos con valor `NULL`, para garantizar el buen funcionamiento de las operaciones `UNION ALL`.
        - En cada bloque **CTE** (`WITH`) mantén el mismo alias con el nombre exacto original que en la base de datos.
        - Si alguna columna de atributos se repite en nombre y en tipo de datos, utiliza el mismo nombre original y comparten tipo de datos aprovecha la misma columna.

        ## 5. Reglas de formato e integridad del script SQL
        - Ajusta el dialecto al motor de base de datos.
        - Utiliza **CTEs** (`WITH`) para descomponer el script en bloques sencillos, claros y reutilizables: bloques de eventos (p. ej., admisiones, altas, medicaciones), operaciones auxiliares, validaciones, etc.
        - Utiliza **CTEs** (`WITH`) adicionales al principio del script si hay validaciones de datos o filtros que afecten a toda una tabla.
        - La última **CTE** ('WITH`) debe ser una operación **`UNION ALL`** para formar el log de eventos final.
        - Especifica el esquema de la base de datos en las operaciones `FROM` y `JOIN`.
        - Orden de columnas en las CTE y en el `UNION ALL` final:
            1. Columnas con los identificadores únicos siempre al principio.
            2. `timestamps`
            3. `activity`
            4. Columnas de Atributos adicionales.
        - Si algún atributo tiene secuencia, NO limites al primer elemento, a no ser que lo especifique el usuario. (ojo con el uso de JOIN o LEFT JOIN si es necesario repetir eventos para mantener la secuencia.)
        - Cuando un atributo no aplique a un evento, rellénalo con `NULL`.
        - Mantén la integridad de los tipos de datos originales en todo el script, mediante EXPLICIT CASTS.
        - Usa los EXPLICIT CASTS óptimos para el dialecto SQL utilizado. (por ejemplo, '1234'::INTEGER en PostgreSQL o `CAST(column_name AS DATE)` en otros dialectos.)
        - Para las relaciones entre tablas usa tiempre nomenclatura estándar de SQL tipo `FROM <A>.<B> <C> <JOIN'S> <ON> <CONDITIONS>`.
        - Usa siempre los nombres originales de las columnas salvo los mapeos indicados de `timestamps` y `activity`, o los mapeos que indique el usuario.
        - Tabula el script SQL para facilitar la lectura de los bloques `CTE`, operaciones `CAST`.
        - Concluye siempre el script con **`SELECT * FROM (…) ORDER BY timestamps ASC;`** al final del script a no ser que el usuario especifique otro orden.
       
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
            Eres un experto en SQL. Revisa el script SQL generado en dialecto PostgreSQL y realiza las correcciones necesarias.

            # Bloque de contexto de necesidades del usuario, conocimientos de la base de datos corporativa y formato del script SQL:
            #################################
            {prompt_sql_generator}

            # Script SQL generado para satisfacer las necesidades del usuario:
            #################################
            {sql_script}

            # Objetivo
            #################################
            En base a:
            - las necesidades del usuario.
            - conocimiento de la base de datos corporativa.
            - formato del script SQL.
            - el primer script SQL generado.

            Revisa en busca de inconsistencias y errores en el script SQL generado.
            - Garantiza el formato del script SQL.
            - Corrige errores de sintaxis SQL.
            - Revisa minuciosamente el apartado de validación de datos, para aplicar los filtros solicitados por el usuario.
            - Revisa minuciosamente que los campos en los bloques `CTEs` (`WITH`) sean consistentes para la ejecución de la consulta final con los `UNION ALL`.
            - Revisa minuciosamente que las operaciones `CAST` estén presentes, sean consistentes y correctas para el dialecto SQL utilizado.
            - Revisa que se respete las operaciones de ordenación especificadas en el contexto.
            - Elimina campos que no haya pedido el usuario.
            - Elimina campos que no se puedan encontrar en el contexto de la base de datos (incluyendo emparejamientos forzados).
            - Garantiza que los alias de las columnas, sean los nombres originales de las columnas del contexto de la base de datos.

            Explica al usuario el contexto del script SQL generado:
            - Comenta todos los bloques de eventos según el contexto de la base de datos.
            - Comenta todos los campos individuales que lo componen,según contexto de la base de datos. (unidad, significado, etc.) (si comparten columna con otro evento, comenta ambos en la misma línea)
            - Indica siempre al principio del script (con: `--` no: `/**/`) los campos y eventos que *NO* se han podido encontrar.
            
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