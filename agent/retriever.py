###############################################
# retriever.py
###############################################

import logging
import os
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from openai import OpenAI

from agent.utils.logging_config import setup_logging

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

class QdrantRetriever:
    """
    RAG: Búsqueda semántica en Qdrant.
    
    Para ayudar a futuros desarrolladores se explica el flujo de trabajo:

    1. Inicialización de la clase QdrantRetriever (__init__):
       1.1. Configuración de parámetros básicos (_setup_configuration).
       1.2. Configuración del proveedor de embeddings (_setup_embedding_provider).
       1.3. Verificación de la existencia de la colección en Qdrant (_verify_collection).

    2. Búsqueda en Qdrant (search):
        2.1. Generación del embedding en función del proveedor (_embed_openai).
        2.3. Búsqueda semántica en Qdrant. (search)

    Nota:
    Se abusa de los logs para facilitar la depuración, puyede ser molesto por consola,
    pero facilita enormemente el sguimiento en este estado inmaduro del proyecto, 
    Facilita el seguimiento de que está ejecutando el agente AI.
    
    Son necesarias las siguientes variables de entorno:
    - EMBEDDING_PROVIDER (Ejemplo: "OPENAI")
    - LOAD_EMBEDDING_MODEL_OPENAI (Ejemplo: "text-embedding-3-small")
    - OPENAI_EMBEDDING_VECTOR_SIZE (Ejemplo: 1536)
    - OPENAI_API_KEY (Ejemplo: "<cadena de caracteres de la API key>")
    - BASE_COLLECTION_NAME (Ejemplo: "<nombre de la colección en Qdrant>")
    """

    def __init__(self) -> None:
        logger.info("Inicializando Retriever (RAG)")
        self._setup_configuration()
        self._setup_embedding_provider()
        self._verify_collection()

    def _setup_configuration(self) -> None:
        """Configura los parámetros básicos del retriever."""
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "OPENAI").upper()
        self.limit = int(os.getenv("RETRIEVER_LIMIT", 25))
        self.client = QdrantClient(url=os.getenv("QDRANT_URL"))
        logger.info(f"Configuración básica completada: limit={self.limit}")

    def _setup_embedding_provider(self) -> None:
        """
        Configura el proveedor de embeddings.
        """
        
        if self.embedding_provider == "OPENAI":
            self.embedding_model = os.getenv("LOAD_EMBEDDING_MODEL_OPENAI", "text-embedding-3-small")
            self._embed = self._embed_openai
            self.vector_size = int(os.getenv("OPENAI_EMBEDDING_VECTOR_SIZE", 1536))
            self._openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.suffix = "openai"
            # Se define el nombre base de la colección (por si en el futuro se incorporan otros proveedores)
            self.base = os.getenv("BASE_COLLECTION_NAME", "qdrant")
            self.collection = f"{self.base}_{self.suffix}"
            self.embedding_tokens = None
            logger.info(f"Proveedor configurado: OpenAI (modelo={self.embedding_model}, colección={self.collection})")
        else:
            logger.error(f"Proveedor todavía no soportado: {self.embedding_provider}")
            raise ValueError(f"Proveedor de embeddings no soportado: {self.embedding_provider}")
    
    def _verify_collection(self) -> None:
        """
        Verifica que la colección existe en Qdrant.
        """
        try:
            self.client.get_collection(self.collection)
            logger.info(f"Colección '{self.collection}' encontrada")
        except Exception:
            logger.warning(f"Colección '{self.collection}' no existe en Qdrant")
    
    def _embed_openai(self, text: str) -> List[float]:
        """
        Genera embeddings usando OpenAI.
        """
        try:
            # Generación del embedding que se usará para la búsqueda semántica
            response = self._openai.embeddings.create(
                model=self.embedding_model, 
                input=text
            )

            vector = response.data[0].embedding

            # Se obtiene el número de tokens usados para generar el embedding
            self.embedding_tokens = response.usage.total_tokens

            # Se obtiene el modelo usado realmente
            self.embedding_model_name = response.model
            
            # Comprobación de tamaño del vector de embedding
            if len(vector) != self.vector_size:
                logger.error(f"Tamaño del vector de embedding inesperado: expected={self.vector_size}, got={len(vector)}")
                raise RuntimeError("Tamaño del vector de embedding inesperado.")
                
            return vector
        except Exception as e:
            logger.error(f"Error generando embedding: {str(e)}")
            raise

    def search(self, query: str, limit: int | None = None, score: float = 0.50) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]:
        """
        Realiza búsqueda semántica en Qdrant.

        Argumentos:
        - query: (str) consulta de búsqueda (debe ser el contexto sacado de las preguntas al usuario)
        - limit: (int o None) opcional, pero se ha pensado para limitar el número de resultados a devolver en la búsqueda.
        - score: (float) opcional, nos ayuda a limitar el score más relevante de los resultados a devolver en la búsqueda.
        Nota sobre el score límite:
        - El score por defecto es 0.50, pero se puede ajustar, en un rango de:
          menos a más relavancia -> 0.00
          más a menos relavancia -> 1.00
        
        Devuelve:
        - results_score_pass: (list) lista de diccionarios con los resultados que pasan el filtro de score de relevancia.
        - results_score_raw: (list) lista de diccionarios con los resultados en bruto, sin filtrar por score de relevancia.
        - score: (float) score de relevancia usado para el filtro.
        """
        limit = limit or self.limit
        # Si nos interesa debuguear que query se está pasando a la búsqueda semántica.
        #logger.info(f"Query: query='{query}')
        logger.info(f"Iniciando búsqueda semántica: limit={limit}, score={score}")

        try:
            # Generación del embedding de la query de contexto
            query_vector = self._embed(query)

            # Búsqueda en Qdrant
            hits = self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=limit,
            )

            # Resultados de la bnúsqueda semántica
            # Resultados que pasan el filtro de score de relevancia
            results_score_pass = [
                {
                    "score": h.score,
                    "module": h.payload.get("module"),
                    "table": h.payload.get("table")
                }
                # Se itera sobre los resultados de la búsqueda y se filtra por score de relevancia
                for h in hits if h.score > score
            ]
            
            # Resultados de la búsqueda semántica
            # Resultados en bruto, sin filtrar por score de relevancia
            results_score_raw = [
                {
                    "score": h.score,
                    "module": h.payload.get("module"),
                    "table": h.payload.get("table")
                }
                # Se itera sobre los resultados de la búsqueda y se filtra por score de relevancia
                for h in hits
            ]

            # Activa si interesa debuguear que está capturando en detalle.
            #logger.info(f"Resultados de la búsqueda: {results_score_pass}")
            
            logger.info(f"Búsqueda en Qdrant completada: {len(results_score_pass)} resultados encontrados")
            
            # Retorna en orden:
            # 1. Resultados que pasan el filtro de score de relevancia.
            # 2. Resultados en bruto, sin filtrar por score de relevancia.
            # 3. Score de relevancia usado para el filtro.
            return results_score_pass, results_score_raw, score

        except Exception as exc:
            logger.error(f"Error en búsqueda semántica: {str(exc)}")
            return []
        
    def get_embedding_tokens (self):
        """
        Devuelve el número de tokens usados para generar el embedding.
        """
        if self.embedding_provider == "OPENAI":
            return self.embedding_tokens
        else:
            return 0
