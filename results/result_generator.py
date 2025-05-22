########################################################
# result_generator.py 
#
# Script para generar los resultados de la evaluación.
#
# Notas de ejecución si te interesa replicar el experimento:
#
# Es necesario que: 
# - La variable de entorno esté activada: DATA_EXPERIMENT = YES
# - Sehayan generado los ficheros TestToolAgent_<uuid>.json en 'output' mediante las invocaciones al AI Agent.
#   (Mira la clase Agent() en agent/agent.py)
# - El entorno virtual del proyecto esté activado, con la versión de Python y las librerías necesarias instaladas. (Leer el README.md)
# - El fichero del dataset de control 'mimicel.csv' se encuentre en 'results/csv/benchmark'
# - Si quieres personalizar alguna ruta, puedes hacerlo en la función main():
#     log_json_path:    ruta al archivo o los archivos json que se generó al trackear la AI Tool,
#                       se ubican en el proyecto en la carpeta output (output/TestToolAgent_<uuid>.json)
#     df_benchmark:     pandas dataframe con el benchmark.
#     ai_csv_dir:       ruta a la carpeta donde se guardan los csv generados por la AI Tool.
#     results_json_dir: ruta a la carpeta donde se guardan los json con los resultados de la evaluación.
#
# Si no se ha generado el fichero de control, se lanzará un error.
# Si se ha generado el fichero de resultados, se guardará en 'results/json/Result_<TestToolAgent_(uuid original)>.json'
#
# Por consola, desde la raíz del proyecto, invoca directamente el script:
# python -m results.result_generator
#
# Sergio Arias Ruiz
# Mayo de 2025
# Versión: 1.0
########################################################    

import json
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
from agent.utils.logging_config import setup_logging
from results.evaluator import EvaluationSQLScripts

# Variables de entorno y logger
load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ResultsSQLScripts:
    """
    Se crea esta clase para poder ejecutar la evaluación de resultados
    de la AI Tool.

    Para iniciarla es necesario pasarle los siguientes parámetros:
    - log_json_path: ruta al archivo json que se generó al trackar la AI Tool,
                     se ubican en el proyecto en la carpeta output (output/TestToolAgent_<uuid>.json)
    - df_benchmark: Pandas DataFrame con el benchmark. 
                    En nuestro caso, se trata del dataset MIMICEL, log de eventos, generado a partir del Módulo ED de MIMIC-IV.
                    Como el dataset analizado es de acceso restringido, en el respositorio del
                    proyecto no se eincluye. Por tanto, si te interesa reproducir el experimento,
                    deberás descargarlo desde el repositorio del proyecto:
                          (versión 2.1.0) https://physionet.org/content/mimicel-ed/2.1.0/ (Módulo ED de MIMIC-IV)
                          (versión 2.2.0) https://physionet.org/content/mimic-iv-ed/2.2/ (benchmark log de eventos de Módulo ED de MIMIC-IV)
                          Es necesario autorización de acceso y curso de formación para acceder a los datos.

    - ai_csv_dir: csv generado tras la ejecución exitosa del script SQL generado por la AI Tool.- Se ubicaría en la carpeta "results/csv/AI_tool/"
    - results_json_dir: ruta del directorio donde su guardará los logs json con los resultados de la evaluación, se ubica en la carpeta "results/json/"

    Al ejecutar la clase, mediante el método run(), se generaran los resultados.

    El archivo `.jsopn` de resultados se guarda con el nombre 'Result_<TestToolAgent_(uuid original)>.json.':
    De esta manera, se pueden auditar los resultados desde el momento de la invocación de la AI Tool.

    ¿Qué guarda el `.json` de resultados?
    Pues es una extensión del archivo ".json" de los logs de la AI Tool, que ya contenían datos interesantes del momento de la invocación,
    y además se generan los datos de las métricas de la evaluación en comparación con el benchmark.

    El archivo `.json` de resultado guarda las siguientes métricas:
    - test_id: id del TestToolAgent (uuid original)
    - evaluation_datetime: fecha y hora de la evaluación.
    - execution_ok: si la SQL se ha ejecutado correctamente o no.

    Del df benchmark:
    - total_rows_benchmark: número de filas del benchmark.
    - columns_list_benchmark: lista única de columnas del benchmark.
    - events_list_benchmark: lista única de eventos del benchmark.
    - columns_num_benchmark: número de columnas del benchmark.
    - events_num_benchmark: número de eventos del benchmark.

    Del df generado por la AI tool:
    - total_rows_ai_tool: número de filas del resultado de la AI Tool.
    - columns_list_ai_tool: lista única de columnas del resultado de la AI Tool.
    - events_list_ai_tool: lista única de eventos del resultado de la AI Tool.
    - columns_num_ai_tool: número de columnas del resultado de la AI Tool.
    - events_num_ai_tool: número de eventos del resultado de la AI Tool.

    Métricas de F1, precision, recall, TP, FP, FN:
    - El detalle de las métricas se encuentra en el archivo evaluator.py

    NOTA 1 IMPORTANTE: Hay un abuso de logger.info() y logger.error() para imprimir los resultados.
    para facilitar el debug, por la extensión de archivos y código.

    NOTA 2 IMPORTANTE: Si replicas el experimento, los `csv` resultantes pesan alrededor de 1GB, si ejecutas el script con el IDE abierto,
    en algunos casos puede saltar error y cerrarte el IDE. ¡No te asustes! :)

    NOTA 3 IMPORTANTE: El proveedor de datos de MIMICEL, no permite la distribución de los datos, por lo que no se incluye en el repositorio.
    """

    def __init__(
        self,
        log_json_path: str,
        df_benchmark: pd.DataFrame,
        ai_csv_dir: str,
        results_json_dir: str,
    ) -> None:
        # Rutas
        self.log_json_path = Path(log_json_path)
        self.df_benchmark = df_benchmark # DataFrame con el benchmark
        self.ai_csv_dir = Path(ai_csv_dir)
        self.results_json_dir = Path(results_json_dir)
        self.ai_csv_dir.mkdir(parents=True, exist_ok=True)
        self.results_json_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Cargar datos de log de la AI Tool
            with self.log_json_path.open(encoding="utf-8") as f:
                self.log_data: Dict[str, Any] = json.load(f)
        except FileNotFoundError as e:
            logger.error(f"No existe el fichero TestToolAgent {self.log_json_path}")
            raise e
        except json.JSONDecodeError as e:
            logger.error(f"Error al cargar los datos del archivo {self.log_json_path}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error inesperado al cargar los datos del archivo {self.log_json_path}: {e}")
            raise e

        # Obtenemos el id del TestToolAgent
        self.test_id = self.log_data.get("id","N/A")

        # Evaluamos el script SQL mejorado generado por la AI Tool
        # Si a alguien le interesa el script intermedio, habría que cambiarlo por "sql_script"
        self.sql_script = self.log_data.get("sql_script_enhanced", "")

        # Cargamos las credenciales de PostgreSQL.
        # LA documentación de MIMICEL utiliza este motor de base de datos para almacenar los datos del módulo ED de MIMIC-IV.
        # Esto no se cambia en nuestro experimento.
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")
        self.db_name = os.getenv("DB_NAME")

        # Por si las moscas, chequeamos, que las credenciales estén bien.
        if not all([self.db_user, self.db_password, self.db_host, self.db_port, self.db_name]):
            logger.error("Credenciales de la base de datos incompletas")
            raise EnvironmentError("Credenciales de la base de datos incompletas")

    # Limpia la SQL, que el trackeo tiene formato markdown
    def _clean_markdown_sql(self, sql: str) -> str:
        sql = sql.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.endswith("```"):
            sql = sql[:-3]
        return sql.strip()

    # Ejecuta lScript SQL
    def _run_sql(self) -> Tuple[int, pd.DataFrame | None]:
        """
        Esta función ejectua el Script SQL, para checkear si la AI Tool ha generado un script SQL válido.
        Si es así, se guarda el CSV con el resultado de la ejecución.

        Esta función tiene que devolvernos una Tupla:
        - 0/1: Si la SQL se ha ejecutado correctamente o no.
        - DataFrame: (Opcional) En el caso de que SQL haya ejecutado correctamente.
        """
        # Instanciamos el motor de base de datos
        engine = create_engine(
            f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        )
        # Limpiamos la SQL, que el trackeo tiene formato markdown
        sql_clean = self._clean_markdown_sql(sql=self.sql_script)
        try:
            # Ejecutamos la SQL
            with engine.connect() as conn:
                result = conn.execute(text(sql_clean))
                df = pd.DataFrame(result.fetchall(), columns=result.keys())

            # Si llegamos aquí, la SQL se ha ejecutado correctamente.
            out_csv = self.ai_csv_dir / f"{self.test_id}.csv"
            df.to_csv(out_csv, index=False)
            logger.info(f"SQL ejecutada correctamente, y se ha generado el `csv` en {out_csv}")

            # Devolvemos 1 (Éxito de ejecución) y el DataFrame con el resultado de la ejecución.
            return 1, df
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            # Devolvemos 0 (Fallo de ejecución) y None
            return 0, None

    # Método principal de la clase, este es el que se ejecuta que ejecuta todo el proceso.
    def run(self) -> Dict[str, Any]:
        execution_ok, df_ai = self._run_sql()

        # Aquí generamos la primera marca de tiempo que será la ejecución de los resultados.
        self.evaluation_datetime = datetime.now().isoformat(timespec="seconds")

        if execution_ok:

            # Llegados a este punto, instanciamos la clase que encapsula las métricas.
            self.evaluator = EvaluationSQLScripts()

            # Iniciamos la carga del dataset benchmark
            df_benchmark = self.df_benchmark

            # Referente al df benchmark
            df_benchmark_total_rows = len(df_benchmark)

            # Capturamos las columnas del df benchmark
            df_benchmark_list_columns = df_benchmark.columns.tolist()

            # Número de columnas del df benchmark
            df_benchmark_num_columns = len(df_benchmark_list_columns)

            # Capturamos los valores únicos de la columna activity
            df_benchmark_list_events = df_benchmark.activity.unique().tolist()

            # Número de eventos únicos del df benchmark
            df_benchmark_num_events = len(df_benchmark_list_events)

            # Referente al df generado por la AI Tool
            df_ai_total_rows = len(df_ai)

            # Capturamos las columnas del df generado por la AI Tool
            df_ai_list_columns = df_ai.columns.tolist()

            # Número de columnas del df generado por la AI Tool
            df_ai_num_columns = len(df_ai_list_columns)

            # Capturamos los valores únicos de la columna activity
            df_ai_list_events = df_ai.activity.unique().tolist()

            # Número de eventos únicos del df generado por la AI Tool
            df_ai_num_events = len(df_ai_list_events)

            # Capturamos las columnas del df generado por la AI Tool
            df_ai_tool_list_columns = df_ai.columns.tolist()

            # Calculamos las métricas
            f1_c, precision_c, recall_c, TP_c, FP_c, FN_c, match_dict_c = self.evaluator._list_elements_metrics_F1(df_benchmark_list_columns, df_ai_tool_list_columns, score_threshold=0.4)
            f1_e, precision_e, recall_e, TP_e, FP_e, FN_e, match_dict_e = self.evaluator._list_elements_metrics_F1(df_benchmark_list_events, df_ai_list_events, score_threshold=0.4)
            coverage = self.evaluator._coverage_total_rows(df_benchmark_total_rows, df_ai_total_rows)

            # Recuperamos el modelo de embeddings usado
            openai_model = self.evaluator.openai_model

            # Eempezamos a construir nuestro diccionario de resultados.
            results = {
                # Identificación de la evaluación.
                "test_id": self.test_id, # ID del TestToolAgent.
                "evaluation_datetime": self.evaluation_datetime,

                # Métrica de ejecución.
                "execution_ok": execution_ok,

                # Métricas de evaluación.
                "coverage": coverage,
                "openai_model": openai_model,
                "columns_f1": f1_c,
                "columns_precision": precision_c,
                "columns_recall": recall_c,
                "columns_TP": TP_c,
                "columns_FP": FP_c,
                "columns_FN": FN_c,
                "events_f1": f1_e,
                "events_precision": precision_e,
                "events_recall": recall_e,
                "events_TP": TP_e,
                "events_FP": FP_e,
                "events_FN": FN_e,
                "columns_num_benchmark": df_benchmark_num_columns,
                "events_num_benchmark": df_benchmark_num_events,
                "columns_num_ai_tool": df_ai_num_columns,
                "events_num_ai_tool": df_ai_num_events,
                "total_rows_benchmark": df_benchmark_total_rows,
                "total_rows_ai_tool": df_ai_total_rows,
                "match_dict_columns": match_dict_c,
                "match_dict_events": match_dict_e,
                "columns_list_benchmark": df_benchmark_list_columns,
                "columns_list_ai_tool": df_ai_list_columns,
                "events_list_benchmark": df_benchmark_list_events,
                "events_list_ai_tool": df_ai_list_events
            }
        else:
            # Diccionario si la ejecución de la SQL es fallida.
            results = {
                # Identificación de la evaluación.
                "test_id": self.test_id, # ID del TestToolAgent.
                "evaluation_datetime": self.evaluation_datetime,

                # Métrica de ejecución.
                "execution_ok": execution_ok,

                # Métricas de evaluación.
                "coverage": 0,
                "columns_f1": 0,
                "columns_precision": 0,
                "columns_recall": 0,
                "columns_TP": 0,
                "columns_FP": 0,
                "columns_FN": 0,
                "events_f1": 0,
                "events_precision": 0,
                "events_recall": 0,
                "events_TP": 0,
                "events_FP": 0,
                "events_FN": 0,
                "columns_num_benchmark": 0,
                "events_num_benchmark": 0,
                "columns_num_ai_tool": 0,
                "events_num_ai_tool": 0,
                "total_rows_benchmark": 0,
                "total_rows_ai_tool": 0,
                "match_dict_columns": {},
                "match_dict_events": {},
                "columns_list_benchmark": [],
                "columns_list_ai_tool": [],
                "events_list_benchmark": [],
                "events_list_ai_tool": []
            }

        # guardar JSON, manteniendo id para mejorar la auditoría de resultados.
        out_json = self.results_json_dir / f"Result_{self.test_id}.json"
        with out_json.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Archivo `json` de resultados, gauardado: {out_json}")
        return results


#  main (Llamada a  la main)
def main():

    # Nombre del archivo benchmark
    file_name = "mimicel.csv"
    path_file = Path("results/csv/benchmark") / file_name

    # Si el fichero de control no existe, lanzamos un error
    if not path_file.is_file():
        logger.error(f"El fichero de control no se ha encontrado: {path_file}")
        raise FileNotFoundError(f"El fichero de control no se ha encontrado: {path_file}")

    # Cargamos el df benchmark
    df_benchmark = pd.read_csv(path_file)

    # Por cada archivo json en la carpeta "output", que empiece por TestToolAgent_
    for file in Path("output").glob("TestToolAgent_*.json"):

        # Instanciamos la clase
        results = ResultsSQLScripts(
            log_json_path=file,
            df_benchmark=df_benchmark,
            ai_csv_dir="results/csv/AI_tool",
            results_json_dir="results/json",
        )
        # Ejecutamos el proceso de generación de resultados
        summary = results.run()
        print(summary)


if __name__ == "__main__":
    main()
