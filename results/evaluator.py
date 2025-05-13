import numpy as np
import os
import pandas as pd
from typing import Tuple
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment
import logging
from dotenv import load_dotenv

load_dotenv()
#setup_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class EvaluationSQLScripts:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = "text-embedding-3-small"

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """
        Devuelve una lista de vectores (embeddings) para una lista de textos.
        Se aprovecha que ya teníamos la api openai configurada.
        """
        client = OpenAI(api_key=self.openai_api_key)
        response = client.embeddings.create(
            input=texts,
            model=self.openai_model
        )
        return np.array([d.embedding for d in response.data])

    def _list_of_elements_cosine_similarity(
        self,
        list_benchmark: list[str],
        list_current: list[str],
    ) -> np.ndarray:
        """
        Calculamos la similitud usando la función de distancia coseno.
        Se la aplicamos a dos listas con los vectores de embeddings:
        - list_benchmark: lista con los vectores de embeddings del benchmark.
        - list_current: lista con los vectores de embeddings de la AI Tool.
        """
        embeddings_benchmark = self._embed_openai(list_benchmark)
        embeddings_current = self._embed_openai(list_current)
        return cosine_similarity(embeddings_benchmark, embeddings_current)

    def _list_elements_metrics_F1(
        self,
        list_benchmark: list[str],
        list_current: list[str],
        score_threshold: float = 0.9,
    ) -> Tuple[float, float, float, int, int, int, dict]:
        """
        Calcula F1-score, precisión y recall para la correspondencia semántica
        entre dos listas de strings.

        Al principio, se intento usar un accuracy puro, era demasiado simplista
        y a la vez dificultaba la medición por las variaciones semánticas que 
        producía nuestra AI Tool.

        El LLM genera strings sinónimos al benchmak, y par amejorar la medición
        se optó par la similitud semántica entre los strings de ambas listas.

        Esto se aplica a la lista de eventos únicos generados y a la lista de nombres de columnas.

        Al tener cierto control en estas listas, podemos aplicar F1 ya que:

        - TP: Verdaderos positivos, podríamos considerar sinónimos los emparejamientos que superen el score_pass.
        Teniendo los TP podríamos considerar:
        - FN: Falsos negativos, serían los elementos del benchmark, que no han sido emparejados. 
              Por tanto loq que nos falta en el benchmark.
        - FP: Falsos positivos, serían los elementos de la AI Tool, que no han sido emparejados. 
              Por tanto elementos incluidos por la AI Tool, no encontrados en el benchmark.

        Gracias a esta interpretación, se puede calcular:
        - precision: (TP / (TP + FP)) de todos los elementos generados por nuetra AI Tool, cuantos estaban realmente en el benchmark.
                     Esta métrica nos viene muy bien para saber si nuestra AI Tool presenta alucinaciones o elementos que nadie ha pedido.
                     De esta manera penalizamos la generación de elementos que no estaban en el benchmark.
                     Valores próximos a 1, indican que nuestra AI Tool se ha comportado como esperábamos.

        - recall: (TP / (TP + FN)) de todos los elementos que pedía el benchmark, cuantos ha sabido generar nuestra AI Tool.
                    Esta métrica nos viene muy bien para medir la cobertura de la AI Tool, respecto a los elementos que esperamos en el benchmark.
                    De esta manera penalizamos la generación de elementos presentes en el benchmark, y que la AI no ha sido capaz de generar.
                    Valores próximos a 1, indican que nuestra AI Tool se ha comportado como esperábamos.

        Extraemos la F1-score como la media armónica de precision y recall.
        - f1: (2 * Precision / (Precision + Recall)) media armónica de precision y recall.
              Con esta métrica, podemos medir como se ha comportado nuestra AI Tool.
              Valores próximos a 1, indican que nuestra AI Tool se ha comportado como esperábamos.
              Valores próximos a 0, indican que nuestra AI Tool presenta alucinaciones severas o no cubre los elementos esperados en nuestro benchmark.

        Necesita como entrada:
        - Una lista de eventos/columnas del benchmark.
        - Una lista de eventos/columnas de la AI Tool.
        - Un score_pass para considerar un emparejamiento como TP.
        - Un diccionario para trackear los emparejamientos encontrados.
        Retornamos una tupla con todas las métricas calculadas.
        """

        try:

            # Validación: ambas listas deben tener al menos un elemento
            if not list_benchmark or not list_current:
                logger.error("No pueden existir listas vacías de elementos")
                raise ValueError("No pueden existir listas vacías de elementos")

            # 1. Matriz de similitud mediante distancia coseno
            matrix_similarity = self._list_of_elements_cosine_similarity(list_benchmark, list_current)

            # 2. Aplicamos el algoritmo de asignación lineal para encontrar el mejor emparejamiento
            cost = 1.0 - matrix_similarity
            rows, cols = linear_sum_assignment(cost)

            # 3. Contamos los elementos que nuestra AI Tool ha generado
            #    y que estaban en el benchmark. (True Positives)
            #    Dado que el LLM puede generar variaciones en las nomenclaturas,
            #    Consideramos que un elemento es TP si supera o iguala el score_pass.
            TP = 0
            match_dict = {}
            # Recorremos la matriz de similitus para verificar si el emparejamiento
            # es un True Positive.
            for r, c in zip(rows, cols):
                # Hacemos pequeña lógica de monitorización
                benchmark_item = list_benchmark[r]
                ai_item = list_current[c]

                # Capturamos si superamos el score, por tanto es un TP
                score_ok = matrix_similarity[r, c] >= score_threshold

                if score_ok:
                    valid = 1
                    TP += 1
                else:
                    valid = 0

                # Guardamos en el diccionario
                match_dict[benchmark_item] = {
                    "ai_column": ai_item,
                    "score": float(matrix_similarity[r, c]),
                    "score_treshold": score_threshold,
                    "pass": valid
                }

            # 4. Calculamos FP (False Positives) y FN (False Negatives)
            FN = len(list_benchmark) - TP  # elementos esperados que no hemos conseguido generar
            FP = len(list_current)   - TP  # elementos generados por nuestra AI Tool, que no estaban en el benchmark

            # 5. Cálculo de precision, recall y F1-score

            # Precisión:
            # Fórmula estándar:Precisión = TP / (TP + FP)
            if TP + FP == 0:
                precision = 0.0
            else:
                precision = TP / (TP + FP)

            # Recall:
            # Fórmula estándar: Recall = TP / (TP + FN)
            if TP + FN == 0: # Seguridad para evitar divisiones por cero
                recall = 0.0
            else:
                recall = TP / (TP + FN)

            # Fórmula estándar: F1 = 2 * P * R / (P + R)
            if precision + recall == 0: # Seguridad para evitar divisiones por cero
                f1 = 0.0
            else:
                f1 = 2 * precision * recall / (precision + recall)

            # Retornamos una tupla con todas las métricas calculadas.
            return f1, precision, recall, TP, FP, FN, match_dict
        
        except Exception as e:
            logger.error(f"Error inesperado al calcular las métricas F1, Precision, Recall, TP, FP y FN: {e}")
            raise Exception(f"Error inesperado al calcular las métricas F1, Precision, Recall, TP, FP y FN: {e}")
        
    def _coverage_total_rows(
        self,
        len_df_benchmark: int,
        len_df_ai: int,
    ) -> float:
        """
        Métrica básica para medir la cobertura de la AI Tool respecto al benchmark.

        Fórmula básica:
        - coverage = (total_rows_ai / total_rows_benchmark)

        ¿Cómo interpretarlarla?
        - Valor 1: (Escenario ideal) Nuestra AI Tool ha generaro el mismo número de filas que nuestro benchmark.
        - Valor <1: Nuestra AI Tool ha generado menos filas que nuestro benchmark.
        - Valor >1: Nuestra AI Tool está generando más filas que nuestro benchmark.

        Si los resultados de F1, precision y recall son buenos, podríamos decir que:

        - Valores cercanos a 1, indican que nuestra AI Tool se ha comportado como esperábamos. Pequeños ajustes
        en la query podrían darnos el resultado esperado.

        - Valores muy por debajo de 1, indican que nuestra AI Tool no ha generado prácticamente ninguna fila.
        Posibles errores en operaciones `JOIN` o `WHERE`.

        - Valores muy por encima de 1, indican que nuestra AI Tool ha generado más filas de las esperadas.
        Posibles errores em operaciones `JOIN` o `WHERE`.
        """

        # Calculamos la métrica
        if len_df_benchmark != 0:
            coverage = len_df_ai / len_df_benchmark
            return coverage
        else:
            coverage = float(0)
            
        return coverage