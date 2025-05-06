###############################################
# load_schema.py
###############################################
#!/usr/bin/env python3
"""load_schema.py
Carga archivos <prefijo modulo>_schema.json de la carpeta knowledge en Qdrant según lista de proveedores.
De momento únicamente soporta OpenAI, pero como al principio del proyecto se probó HuggingFace,
se ha dejado implementado la subida multiproveedor.

Si se usan varios proveedores, guarda el nombre de la colección con el sufijo del proveedor.

Guía rápida de uso:
- Invoca el comando `python -m scripts.load_schema.py` en el entorno virtual del proyecto.
"""
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from agent.loader import QdrantLoader
from agent.utils.logging_config import setup_logging

# Configuración global de logging
setup_logging()
logger = logging.getLogger("load_schema")

load_dotenv()  # Variables de entorno desde .env

def main() -> None:
    # Buscamos todos los archivos *_schema.json en la carpeta knowledge
    knowledge_dir = Path("knowledge")

    # Si no encontramos carpeta knowledge, salimos
    if not knowledge_dir.exists():
        logger.error(f"No se encontró el directorio {knowledge_dir}")
        sys.exit(1)

    # Usamos .glob de Path, para crear lista con los archivos detectados.
    schema_files = list(knowledge_dir.glob("*_schema.json"))

    # si nmo se ecuentran salimos de le ejecución
    if not schema_files:
        logger.error("No se encontraron archivos *_schema.json en la carpeta knowledge")
        sys.exit(1)

    # Log de control de archivos detectados
    logger.info(f"Se encontraron {len(schema_files)} archivos schema:")
    for schema_file in schema_files:
        logger.info(f"- {schema_file.name}")

    # lista de proveedores para cargar, de momento solo se ha implementado openai
    providers = ["openai"]

    # Esto se ha diseñádo ya que al principio del proyecto se probó HuggingFace,
    # Se ha dejado implementada por si a alguien le interesa subir varios proveedores.
    # Se guardan en Qdrant con el mismo nombre de la colección pero con sufijo 
    # propio del proveedor.
    for provider in providers:
        logger.info(f"Proveedor: {provider}")
        # Creamos el loader una sola vez por proveedor
        loader = QdrantLoader(provider, reset_collection=True)  # Solo reset en la primera creación
        
        # Esta parte cargará a Qdrant cada archivo `<prefijo modulo>_schema` detectado.
        for schema_file in schema_files:
            logger.info(f"Cargando schema: {schema_file.name}")
            try:
                # Si se pasamops esquemas adicionales, la colección solo se resetea 
                # en el primer elemento. Para el resto de _schema.json se carga
                # sin resetear la colección.
                if schema_file != schema_files[0]:
                    loader = QdrantLoader(provider, reset_collection=False)
                loader.load_schema(schema_file)
                logger.info(f"Schema {schema_file.name} cargado exitosamente.")
            except Exception as e:
                logger.error(f"Error cargando schema {schema_file.name}: {str(e)}")
                # Continuamos con el siguiente schema aunque falle uno
                continue

        logger.info(f"Proceso finalizado para el proveedor {provider}.")

if __name__ == "__main__":
    main()