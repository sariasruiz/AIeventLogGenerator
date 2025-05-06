###############################################
# logging_config.py
###############################################
import logging

def setup_logging():
    """Configuración estándar de logging para el proyecto"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ) 