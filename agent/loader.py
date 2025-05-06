###############################################
# loader.py
###############################################

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI
from agent.utils.logging_config import setup_logging
from agent.experiment_log import Experiment_LoadKnowledge, is_experiment_enabled

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

class QdrantLoader:
    """
    Carga y gestiona conocimiento en Qdrant usando embeddings.
    Se crea un solo embedding para cada tabla y se sube a qdrant.
    Se hace de esta manera para que el RAG sea más eficiente,
    para mantener el contexto de los campos dentor de su contexto
    inmediato.

    1. Primero se realiza la configuración básica: proveedor de embeddings y cliente Qdrant. (_setup_configuration)
    2. Luego se configura parámetros según el proveedor de embeddings. (_setup_embedding_provider)
    3. Se limpia colección (en el caso de que reset_collection sea True) y vuelve a crear la colección en Qdrant. (_reset_collection)
    4. Finalmente se carga el esquema en Qdrant. (load_schema)

    Requiere las siguientes variables de entorno:
    - BASE_COLLECTION_NAME: Nombre base para la colección en Qdrant
    - QDRANT_URL: URL del servidor Qdrant
    - LOAD_EMBEDDING_MODEL_OPENAI: Modelo de embeddings de OpenAI
    - OPENAI_EMBEDDING_VECTOR_SIZE: Tamaño del vector de embeddings
    - OPENAI_API_KEY: Clave API de OpenAI
    """

    def __init__(self, embedding_provider: str = "openai", reset_collection: bool = True) -> None:
        """
        Inicializa el cargador de esquemas.
        
        Argumentos:
            embedding_provider (str): Proveedor de embeddings ('openai' por defecto)
            reset_collection (bool): Si es True, borra y vuelve a crear la colección.
        """
        self._setup_configuration(embedding_provider)
        self._setup_embedding_provider()

        # Punto de interés:
        # Si reset_collection es True, se borra y recrea la colección al inicio.
        # Si reset_collection es False, se insertan los vectores en la colección sin borrar la existente.
        if reset_collection:
            self._reset_collection()

        #########################################################
        # Punto de control 1 monitorización de carga de conocimiento
        #########################################################
        try:    
            if is_experiment_enabled():
                self.experiment = Experiment_LoadKnowledge()
                self.experiment.add_load_knowledge_start()
        except Exception as e:
            logger.error(f"Error en experiment.add_load_knowledge_start: {str(e)}")
        #########################################################

    def _setup_configuration(self, embedding_provider: str) -> None:
        """
        Configura los parámetros básicos del loader: 
        Proveedor de embeddings y cliente Qdrant.
        
        Argumentos:
            embedding_provider (str): Proveedor de embeddings
        """
        self.embedding_provider = embedding_provider.lower()
        self.client = QdrantClient(url=os.getenv("QDRANT_URL"))

    def _setup_embedding_provider(self) -> None:
        """
        Configuración del proveedor de embeddings.
        """        
        if self.embedding_provider == "openai":
            self.model_name = os.getenv("LOAD_EMBEDDING_MODEL_OPENAI", "text-embedding-3-small")
            self.vector_size = int(os.getenv("OPENAI_EMBEDDING_VECTOR_SIZE", 1536))
            self._model = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self._embed = self._embed_openai
            
            # Configuración del nombre de la colección
            base = os.getenv("BASE_COLLECTION_NAME", "test")
            self.collection = f"{base}_{self.embedding_provider}"
            
        else:
            logger.error(f"Proveedor de embeddings todavía no soportado: {self.embedding_provider}")
            raise ValueError(f"Proveedor de embeddings todavía no soportado: {self.embedding_provider}")

    def _embed_openai(self, text: str) -> List[float]:
        """
        Generación de embedding con proveedor OpenAI.
        
        Argumentos:
            text (str): Texto para generar embedding
        """

        self.text_for_embedding = text

        try:
            response = self._model.embeddings.create(
                model=self.model_name,
                input=self.text_for_embedding
            )
            # Se obtiene el vector de embedding
            self.vector = response.data[0].embedding
            
            # Se obtiene el número de tokens, modelo real y tamaño del vector
            self.embedding_tokens = response.usage.total_tokens
            self.embedding_model_name = response.model
            self.embedding_vector_size = len(self.vector)
            
            # Verificación de tamaño del vector
            if self.embedding_vector_size != self.vector_size:
                logger.error(
                    f"Tamaño del vector incorrecto: esperado={self.vector_size}, recibido={self.embedding_vector_size}"
                )
                raise RuntimeError("Tamaño del vector de embedding inesperado")
                
            return self.vector
        except Exception as e:
            logger.error(f"Error generando embedding: {str(e)}")
            raise

    def _reset_collection(self) -> None:
        """
        Borra colección (si existe) y la recrea nuevamente en Qdrant.
        """
        try:
            self.client.delete_collection(self.collection)
        except Exception:
            logger.info(f"Colección a crear es nueva: {self.collection}")

        try:
            # Configuración del modelo de vectorización
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    # Usamos distancia coseno para que el RAG sea más eficiente
                    distance=models.Distance.COSINE
                ),
            )

            logger.info(f"Colección creada exitosamente: {self.collection}")
        except Exception as e:
            logger.error(f"Error creando colección en Qdrant: {str(e)}")
            raise

    def load_schema(self, schema_path: Path | str) -> None:
        """
        Carga el esquema en Qdrant.
        Primero genera un texto amigable para convertirlo a vector (embedding)
        y luego se crea el payload con toda la información del schema relacionado.

        Aquí, lo que se intenta es crear un único vector por tabla, ya que
        un campo por sí solo no tiene sentido, y requiere de su cotnexto inmediato.
        
        Argumentos:
            schema_path (Path | str): Ruta al archivo schema.json
        """
        try:
            # Cargamos schema.json
            schema = json.loads(Path(schema_path).read_text("utf-8"))
            
            # Definimos la lista de puntos a subir a qdrant vacía
            points = []
            for table in schema["module"]["tables"]:
                # Generamos el texto para embedding de manera bilingüe
                text = (
                    f"Module: {schema['module']['id']}\n"
                    f"Description (EN): {schema['module']['description']['english']}\n"
                    f"Description (ES): {schema['module']['description']['spanish']}\n"
                    f"Table: {table['name']}\n"
                    f"Definition (EN): {table['definition']['english']}\n"
                    f"Definition (ES): {table['definition']['spanish']}\n"
                    f"Purpose (EN): {table['purpose']['english']}\n"
                    f"Purpose (ES): {table['purpose']['spanish']}\n"
                    f"Fields:\n" + "\n".join(
                        f"- {field['name']} ({field['type']}):\n"
                        f"  EN: {field['description']['english']}\n"
                        f"  ES: {field['description']['spanish']}"
                        # Pese a que el schema.json es mucho más rico y complejo,
                        # Únicamente se deciden añadir los cambos en lenguaje natural anteriores
                        # Y técnicos los correspondientes a rango de valores, valores textuales más frecuentes
                        # El resto de variables se omiten para un usuario final no familiarizado con la estructura de la base de datos.
                        f"  Range: {field.get('range', 'N/A')}\n"
                        f"  Most Frequent Values: {', '.join(str(v.get('value', '')) for v in field.get('most_frequent_values', [])) or 'N/A'}\n"
                        # Se itera sobre los campos de la tabla para generar el text
                        # para calcular el vector de embedding
                        for field in table['fields']
                    )
                )
                
                # Creamos el payload con toda la información de la tabla
                # En este caso, con toda la riqueza del schema .json, 
                # para que el LLM pueda usarlo en caso de ser necesario.
                payload = {
                    "type": "table_info",
                    "last_updated": schema["last_updated"],
                    "module": {
                        "id": schema["module"]["id"],
                        "schema_db": schema["module"]["schema_db"],
                        "description": schema["module"]["description"]
                    },
                    "table": {
                        "name": table["name"],
                        "definition": table["definition"],
                        "purpose": table["purpose"],
                        "fields": [
                            {
                                "name": field["name"],
                                "type": field["type"],
                                "nullable": field["nullable"],
                                "is_pk": field["is_pk"],
                                "is_fk": field["is_fk"],
                                "description": field["description"],
                                "link_to": field.get("link_to", []),
                                "link_from": field.get("link_from", []),
                                "range": field.get("range", {}),
                                "distinct_values": field.get("distinct_values", []),
                                "most_frequent_values": field.get("most_frequent_values", [])
                            }
                            # Se itera sobre los campos de la tabla para generar el payload
                            for field in table["fields"]
                        ]
                    }
                }
                
                # Se crea el punto para subir a qdrant
                points.append({
                    "id": str(uuid4()), # Se crea un id único para cada punto para no reptirse ni complicar la carga
                    "vector": self._embed(text), # se genenera el vector
                    "payload": payload # se crea el payload con toda la información de la tabla
                })

                # Se almacenan el diccionario de puntos subidos a Qdrant
                self.points = points
            
            ########################################################
            # Punto de control 2 Inicio de carga de conocimiento
            #########################################################
            try:
                if is_experiment_enabled():
                    self.experiment.add_load_knowledge_start()
            except Exception as e:
                logger.error(f"Error en experiment.add_load_knowledge_start: {str(e)}")

            #########################################################
            
            # Subimos los puntos a qdrant
            self.client.upsert(self.collection, points)

            #########################################################
            # Punto de control 3 Fin de carga de conocimiento
            #########################################################
            try:
                if is_experiment_enabled():
                    self.experiment.add_load_knowledge_finish()
            except Exception as e:
                logger.error(f"Error en experiment.add_load_knowledge_finish: {str(e)}")

            # Finalizamos el experimento
            try:
                if is_experiment_enabled():
                    self.experiment.finish(
                        name_collection=self.collection,
                        embedding_provider=self.embedding_provider,
                        embedding_model_name=self.embedding_model_name,
                        embedding_vector_size=self.embedding_vector_size,
                        embedding_tokens=self.embedding_tokens,
                        text_for_embedding=self.text_for_embedding,
                        points=self.points
                    )
            except Exception as e:
                logger.error(f"Error en experiment.finish: {str(e)}")
            #########################################################

            logger.info(f"Esquema de {schema['module']['id']} cargado exitosamente: {len(points)} puntos")
            
        except Exception as e:
            logger.error(f"Error cargando esquema: {str(e)}")
            raise 