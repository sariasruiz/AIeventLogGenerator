###############################################
# experiment_log.py
###############################################

import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Any

# Configuración de logging
logger = logging.getLogger(__name__)

class Experiment:
    """
    Clase para registrar y gestionar experimentos de generación de SQL.
    """
    
    def __init__(self, user_needs: str):
        """
        Inicializamos un nuevo experimento.
        Capturamos los primeros datos de control:
        - ID del experimento (único con uuid)
        - Fecha y hora de inicio del experimento.
        - Marca de tiempo de inicio del experimento.
        - Necesidades del usuario.

        Argumentos:
            user_needs (str): Recibe el resumen de las necesidades del usaurio 
                              después de lanzarle las preguntas metodológicas.
        """
        self.id = "TestToolAgent_" + str(uuid.uuid4())
        self.datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.start_time = time.perf_counter()
        self.user_needs = user_needs
        
        # Crear directorio output si no existe
        # Como va a invocarse desde streamlit chatbot.py hay que hacer 2 parents.
        base_dir = Path(__file__).parent.parent
        self.output_dir = base_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"Experimento iniciado: {self.id}")

    def add_retriever_start(self) -> None:
        """
        Captura marca de tiempo de inicio de la búsqueda del retriever.
        """

        self.start_time_retriever = time.perf_counter()

    def add_retriever_finish(
            self, 
            result_pass: List[Dict[str, Any]],
            result_raw: List[Dict[str, Any]],
            score_limit: float,
            embedding_model: str,
            embedding_tokens: int
        ) -> None:
        """
        Registra el fin de la búsqueda del retriever y sus resultados.
        Se captura:
        - Marca de tiempo de fin de la búsqueda del retriever.
        - Número de resultados que pasan el filtro de score de relevancia.
        - Resultado de la búsqueda.
        - Scores de todas las tablas. (haya pasado el corte o no)
        - Score límite que marca el corte `> score_limit`
        """
        # Se precualcula el número de resultados que pasan el filtro de score de relevancia.
        count_pass = len(result_pass)

        # Precapturamos resumen de la búsqueda semántica.
        results_summary_pass = []
        results_summary_raw = []

        # Tablas que han pasado el filtro con su score
        # De esta manera se puede auditar que elementos tenía en schema.json
        for item in result_pass:
            summary_pass = {
                "score": item.get("score"),
                "module_id": item.get("module", {}).get("id"),
                "schema_db": item.get("module", {}).get("schema_db"),
                "table_name": item.get("table", {}).get("name")
            }
            results_summary_pass.append(summary_pass)

        # Tablas en bruto con su score
        # Igualmente, se puede auditar que elementos tenía en schema.json
        for item in result_raw:
            summary_raw = {
                "score": item.get("score"),
                "module_id": item.get("module", {}).get("id"),
                "schema_db": item.get("module", {}).get("schema_db"),
                "table_name": item.get("table", {}).get("name")
            }
            results_summary_raw.append(summary_raw)
        
        # Calculamos el tiempo transcurrido desde el inicio de la búsqueda del retriever.
        self.finish_time_retriever = time.perf_counter()
        self.retriever_score_count_pass = count_pass
        self.retriever_result_search_pass = results_summary_pass
        self.retriever_result_search_raw = results_summary_raw
        self.retriever_score_limit = score_limit
        self.retriever_embedding_model = embedding_model
        self.retriever_embedding_tokens = embedding_tokens
        # Precapturamos el precio por millón de tokens del modelo de embedding.
        # Valor de Input, ya que embedding no tiene output.
        self.retriever_embedding_price_1M_tokens = price_1M_tokens_openai(self.retriever_embedding_model)[0]
    
    def add_sql_generator_start(self) -> None:
        """
        Marca de tiempo de inicio de la generación del primer SQL.
        """

        self.start_time_sql_generator = time.perf_counter()

    def add_sql_generator_finish(
            self,
            prompt: str, 
            sql_script: str, 
            metadata_llm: Dict[str, Any]) -> None:
        """
        Captura las siguientes métricas de control:
            - Marca de tiempo del fin de la generación del primer SQL.
            - Prompt usado para generar el primer SQL.
            - Script SQL generado.
            - Metadata de la invocación del LLM.
        """
        self.finish_time_sql_generator = time.perf_counter()
        self.prompt_sql_generator = prompt
        self.sql_script = sql_script
        # Por precaución, en caso de que la estructura cambiue según el proveedor de LLM.
        if os.getenv("SQL_LLM_PROVIDER", "OPENAI").upper() == "OPENAI":
            self.sql_script_model_name = metadata_llm.get("model_name", "")
            self.sql_script_total_tokens = metadata_llm.get("token_usage", {}).get("total_tokens", 0)
            self.sql_script_prompt_tokens = metadata_llm.get("token_usage", {}).get("prompt_tokens", 0)
            self.sql_script_completion_tokens = metadata_llm.get("token_usage", {}).get("completion_tokens", 0)
            price_1M_tokens = price_1M_tokens_openai(self.sql_script_model_name)
            self.sql_script_price_1M_tokens_input = price_1M_tokens[0]
            self.sql_script_price_1M_tokens_output = price_1M_tokens[1]

    def add_sql_enhanced_start(self) -> None:
        """
        Captura la marca de tiempo de inicio de la generación del SQL mejorado.
        """
        self.start_time_sql_generator_enhanced = time.perf_counter()

    def add_sql_enhanced_finish(
            self, 
            prompt: str, 
            sql_script: str, 
            metadata_llm: Dict[str, Any]
            ) -> None:
        """
        Captura las métricas de control a la finalización del SQL mejorado:
        - Marca de tiempo de fin de la generación del SQL mejorado.
        - Prompt usado para generar el SQL mejorado.
        - Script SQL mejorado.
        - Metadata de la invocación del LLM.
        """

        self.finish_time_sql_generator_enhanced = time.perf_counter()
        self.prompt_sql_generator_enhanced = prompt
        self.sql_script_enhanced = sql_script

        # Por precaución, en caso de que la estructura cambiue según el proveedor de LLM.
        if os.getenv("SQL_LLM_PROVIDER", "OPENAI").upper() == "OPENAI":
            self.sql_script_enhanced_model_name = metadata_llm.get("model_name", "")
            self.sql_script_enhanced_total_tokens = metadata_llm.get("token_usage", {}).get("total_tokens", 0)
            self.sql_script_enhanced_prompt_tokens = metadata_llm.get("token_usage", {}).get("prompt_tokens", 0)
            self.sql_script_enhanced_completion_tokens = metadata_llm.get("token_usage", {}).get("completion_tokens", 0)
            price_1M_tokens = price_1M_tokens_openai(self.sql_script_enhanced_model_name)
            self.sql_script_enhanced_price_1M_tokens_input = price_1M_tokens[0]
            self.sql_script_enhanced_price_1M_tokens_output = price_1M_tokens[1]


    def finish(self) -> None:
        """
        Se capturan las últimas métricas de control al concluir el experimento:
        - Marca de tiempo de fin del experimento. (generación de SQL mejorado)
        - Tiempo total del experimento. (respecto a la marca de tiempo de inicio)
        - Tiempo de generación del primer SQL.)
        - Tiempo de generación del SQL mejorado.
        - Tiempo de búsqueda del retriever.
        - Coste total de los SQL generados.

        Se construye el json con los datos de control del experimento.
        """
        finish_time = time.perf_counter()
        self.finish_time = finish_time
        
        # Tiempo total del experimento.
        self.total_time = round(self.finish_time - self.start_time, 6)
        
        # Tiempo de búsqueda del retriever.
        self.retriever_time = round(self.finish_time_retriever - self.start_time_retriever, 6)
        
        # Tiempo de generación del primer SQL.
        self.sql_generation_time = round(self.finish_time_sql_generator - self.start_time_sql_generator, 6)
        
        # Tiempo de generación del SQL mejorado.
        self.sql_enhanced_time = round(self.finish_time_sql_generator_enhanced - self.start_time_sql_generator_enhanced, 6)
        
        # Definimos coste total 0 por defecto por si alguno no se puede calcular.
        self.total_cost = 0
        self.sql_generation_cost = 0
        self.sql_enhanced_cost = 0
        self.retriever_embedding_cost = 0

        # Coste de la generación del primer SQL.
        self.sql_generation_cost_input = (self.sql_script_prompt_tokens * self.sql_script_price_1M_tokens_input) / 1000000
        self.sql_generation_cost_output = (self.sql_script_completion_tokens * self.sql_script_price_1M_tokens_output) / 1000000
        self.sql_generation_cost = self.sql_generation_cost_input + self.sql_generation_cost_output
        
        # Coste de la generación del SQL mejorado.
        self.sql_enhanced_cost_input = (self.sql_script_enhanced_prompt_tokens * self.sql_script_enhanced_price_1M_tokens_input) / 1000000
        self.sql_enhanced_cost_output = (self.sql_script_enhanced_completion_tokens * self.sql_script_enhanced_price_1M_tokens_output) / 1000000
        self.sql_enhanced_cost = self.sql_enhanced_cost_input + self.sql_enhanced_cost_output

        # Coste de la creación del embedding para la búsqueda semántica.
        self.retriever_embedding_cost = (self.retriever_embedding_tokens * self.retriever_embedding_price_1M_tokens) / 1000000
        
        # Coste total de la Tool en tokens: Script SQL 1 + Script SQL 2 + Búsqueda semántica.
        self.total_cost = self.sql_generation_cost + self.sql_enhanced_cost + self.retriever_embedding_cost

        # Creamos el json con los datos de control del experimento.
        self.data = {
            "id": self.id,
            "datetime": self.datetime,
            # LLM
            "llm_model_retriever_embedding": self.retriever_embedding_model,
            "llm_model_sql_generator": self.sql_script_model_name,
            "llm_model_sql_generator_enhanced": self.sql_script_enhanced_model_name,
            # Tiempos
            "time_in_seconds_total": self.total_time,
            "time_in_seconds_retriever": self.retriever_time,
            "time_in_seconds_sql_generation": self.sql_generation_time,
            "time_in_seconds_sql_generation_enhanced": self.sql_enhanced_time,

            # Medidas token de la herramienta
            "tokens_total_retriever_embedding": self.retriever_embedding_tokens,
            "tokens_total_sql_generation": self.sql_script_total_tokens,
            "tokens_prompt_sql_generation": self.sql_script_prompt_tokens,
            "tokens_completion_sql_generation": self.sql_script_completion_tokens,
            "tokens_total_sql_generation_enhanced": self.sql_script_enhanced_total_tokens,
            "tokens_prompt_sql_generation_enhanced": self.sql_script_enhanced_prompt_tokens,
            "tokens_completion_sql_generation_enhanced": self.sql_script_enhanced_completion_tokens,
            "tokens_total_tool": self.retriever_embedding_tokens + self.sql_script_total_tokens + self.sql_script_enhanced_total_tokens,

            # Coste de Tokens de la Tool en dólares.
            "total_cost_retriever_embedding_in_dollars": self.retriever_embedding_cost,
            "total_cost_sql_generation_in_dollars": self.sql_generation_cost,
            "total_cost_sql_generation_enhanced_in_dollars": self.sql_enhanced_cost,
            "total_cost_tool_in_dollars": self.total_cost,

            # Necesodad del usuario.
            "prompt_user_needs": self.user_needs,

            # Resultados de la búsqueda del retriever.
            "retriever_score_limit": self.retriever_score_limit,
            "retriever_score_count_pass": self.retriever_score_count_pass,
            "retriever_pass_summary": self.retriever_result_search_pass,
            "retriever_raw_summary": self.retriever_result_search_raw,

            # Prompt para generar el primer SQL y script SQL generado.
            "prompt_sql_generator": self.prompt_sql_generator,
            "sql_script": self.sql_script,

            # Prompt para generar el SQL mejorado y script SQL mejorado.
            "prompt_sql_generator_enhanced": self.prompt_sql_generator_enhanced,
            "sql_script_enhanced": self.sql_script_enhanced,
            "result": "unkown"
        }
        # Preparamos la estructura para la exportación de los datos.
        filename = f"{self.id}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Experimento finalizado y guardado: {filename}")

class Experiment_LoadKnowledge:

    def __init__(self):
        """
        Inicializamos monitorización de carga de conocimiento.
        """
        self.id = "LoadKnowledge_" + str(uuid.uuid4())
        self.datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.start_time = time.perf_counter()

        # Crear directorio output si no existe
        # Como en este caso se invoca por consola, usamos ruta relativa.
        # Nota: ver el base_dir en Experiment, para ver diferencia con streamlit.
        base_dir = Path("output")
        self.output_dir = base_dir
        self.output_dir.mkdir(exist_ok=True)

    def add_load_knowledge_start(self) -> None:
        """
        Captura marca de tiempo de inicio de la carga de conocimiento.
        """
        self.start_time_load_knowledge = time.perf_counter()
    
    def add_load_knowledge_finish(self) -> None:
        """
        Captura marca de tiempo de fin de la carga de conocimiento.
        """
        self.finish_time_load_knowledge = time.perf_counter()
    
    def finish(
            self,
            name_collection: str,
            embedding_provider: str,
            embedding_model_name: str,
            embedding_vector_size: int,
            embedding_tokens: int,
            text_for_embedding: str,
            points: List[Dict[str, Any]]
        ) -> None:
        """
        Se capturan las últimas métricas de control al concluir
        la carga de conocimiento:
        - Nombre de la colección de Qdrant.
        - Nombre del modelo de embedding utilizado.
        - Tamaño del vector de embedding utilizado.
        - Número de tokens usados para generar los embeddings.
        - Texto usado para generar el embedding.
        - Vector generado.
        - Número de puntos subidos a Qdrant.
        """
        # Tiempo total del proceso de carga de conocimiento.
        self.total_time = round(self.finish_time_load_knowledge - self.start_time, 6)

        # Tiempo de carga de conocimiento.
        self.time_load_knowledge = round(self.finish_time_load_knowledge - self.start_time_load_knowledge, 6)

        # Nombre de la colección de Qdrant.
        self.name_collection = name_collection

        # Proveedor de embedding.
        self.embedding_provider = embedding_provider

        # Nombre del modelo de embedding utilizado.
        self.embedding_model_name = embedding_model_name

        # Tamaño del vector de embedding utilizado.
        self.embedding_vector_size = embedding_vector_size

        # Texto usado para generar el embedding.
        self.text_for_embedding = text_for_embedding

        # Número de tokens usados para generar los embeddings.
        self.embedding_tokens = embedding_tokens

        # Puntos subidos a Qdrant.
        self.points = points

        # Precio por millón de tokens del proveedor de embedding.
        self.price_1M_tokens_in_dollars = price_1M_tokens_openai(self.embedding_model_name)[0]

        # Coste de la carga de conocimiento en dólares.
        self.cost_load_knowledge_in_dollars = (self.embedding_tokens * self.price_1M_tokens_in_dollars) / 1000000

        # Creamos el json con los datos de control de la carga en Qdrant.
        self.data = {
            "id": self.id,
            "datetime": self.datetime,
            "time_in_seconds_load_knowledge": self.time_load_knowledge,
            "time_in_seconds_total": self.total_time,
            "name_collection": self.name_collection,
            "embedding_provider": self.embedding_provider,
            "embedding_model_name": self.embedding_model_name,
            "embedding_vector_size": self.embedding_vector_size,
            "embedding_tokens": self.embedding_tokens,
            "embedding_cost_in_dollars": self.cost_load_knowledge_in_dollars,
            "text_for_embedding": self.text_for_embedding,
            "points": self.points
        }

        # Preparamos la estructura para la exportación de los datos.
        filename = f"{self.id}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Monitorización de carga de conocimiento finalizada y guardada: {filename}")

def is_experiment_enabled() -> bool:
    """
    Se verifica desde variable de entorno si se debe monitorizar el experimento.
    """
    return os.getenv("DATA_EXPERIMENT", "YES").upper() == "YES" 

def price_1M_tokens_openai(model_name: str) -> float:
    """
    Devuelve el precio en dólares por millón de tokens para un modelo de LLM.
    Según documentación oficial de OpenAI:
    https://openai.com/api/pricing/

    Nota: Valor 0 implica que no existe funcionalidad o no se dispone del precio.
    """
    if model_name == "o4-mini-2025-04-16":
        update = datetime(2025, 5, 4)
        price_input = 1.10
        price_output = 4.40
    elif model_name == "gpt-4o-mini-2024-07-18":
        update = datetime(2025, 4, 16)
        price_input = 0.15
        price_output = 0.60
    elif model_name == "text-embedding-3-small":
        update = datetime(2025, 5, 4)
        price_input = 0.02
        price_output = 0
    else:
        update = datetime(2025, 5, 4)
        price_input = 0
        price_output = 0

    return price_input, price_output, update