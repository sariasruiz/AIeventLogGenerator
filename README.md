# Documentación del Proyecto

**Autor:** Sergio Arias Ruiz

**Email:** sariasri@uoc.edu

**Fecha:** Mayo 2025

**Licencia:** [Apache 2.0](LICENSE.md)

**Demo:** [http://chatbot.sergioarias.eu](https://chatbot.sergioarias.eu)


## Acceso a la Demo

Si deseas acceder a la demo real del chat, por favor envía un correo electrónico al autor con el asunto "Acceso al Chat AI Event Log Generetor". Te proporcionaremos las credenciales necesarias para acceder a la versión en producción.

Es indispensable enviar el correo de solicitud desde una **dirección de email válida del dominio uoc.edu**.

## Descripción

Este proyecto implementa un chat para interactuar con un AI Agent que tiene como misión principal generar scripts SQL para construir logs de eventos compatibles con el Process Mining.

Para lograrlo, el AI Agent realiza 5 preguntas metodológicas en lenguaje natural y utiliza técnicas RAG (Retrieval Augmented Generation) para recuperar información relevante de la base de datos y generar los scripts SQL mediante dos LLM razonadores.

## Resumen y objetivo del proyecto

Aplicación de técnicas novedosas a la disciplina del Process Mining en el ámbito hospitalario.
En la revisión de literatura se observa una baja adopción del Process Mining en el sector hospitalario, causado principalmente por **la complejidad en la elaboración de logs de eventos.** 

- La información en los sistemas de información hospitalaria (HIS), suelen estar repartidas por decenas de tablas, dificultando la obtención de información de extremo a extremo.
- La construcción de scripts SQL que permiten la extracción, continúa siendo un proceso tedioso y pesado.

Se intenta explorar en un entorno controlado si la Inteligencia Artificial Generativa, mediante técnicas de Generación Aumentada por Recuperación pueden ayudar en la construcción de estos logs de eventos, **conectando la IA al conocimiento estructural de una base de datos hospitalaria**. 

**Al aislar su aplicación a nivel estructural de una base de datos, se garantiza en todo momento la privacidad de los datos del paciente**.

Como elemento de control y validar la exploración, se intenta reproducir el log de eventos del *estudio de referencia*:
[MIMICEL: MIMIC-IV Event Log for Emergency Department](https://physionet.org/content/mimicel-ed/2.1.0/)

MIMICEL, construye un log de eventos del módulo de urgencias a partir del conjunto de datos MIMIC-IV.

El conjunto de datos  [MIMIC-IV](https://physionet.org/content/mimiciv/3.1/) es una base de datos relacional real hospitalaria anonimizada gestionada principalmente por el MIT.

MIMIC-IV, se compone principalmente de 37 tablas en diferentes módulos, con datos de más de 200 mil paciente admitidos en urgencias y más de 65 mil pacientes admitidos en curas intensivas.

- ED: Módulo de Urgencias.
- HOSP: Módulo Hospitalización.
- ICU: Módulo de Curas Intensivas.

Para esta investigación se explora la viabilidad de la idea únicamente para el departamento `ED` de Urgencias.

## Limitaciones de aplicación de la IA generativa en el conjunto de Datos MIMIC-IV

**[AVISO IMPORTANTE]** Los proveedores del conjunto de datos prohíben expresamente aplicar IA Generativa directamente sobre los datos del conjunto de datos usando API's de proveedores externos como OpenAI, para garantizar la privacidad del paciente y el cumplimento de las normas HIPAA.

Por ese motivo, **para garantizar el cumplimiento de las políticas en materia de datos personales y privacidad del paciente**, exclusivamente se aplica IA Generativa, sobre los datos de estructura de la base de datos. Para el caso que nos aplica, datos públicos y accesibles de la propia documentación del proyecto [Doc MIMIC-IV](https://mimic.mit.edu/docs/):

- Nombre esquema de base datos.
- Descripciones de módulos y tablas.
- Nombres y descripciones de campos que la componen.
- Relaciones de las tablas y campos.

**El modelo de AI, únicamente tiene acceso a un `.json` aislado** con la información estructural, y **de ninguna manera se le otorga acceso a herramientas con acceso a la base de datos** que contiene la información.

**En este experimento, el agente devuelve de manera directa un script SQL** con la finalidad que únicamente los usuarios autorizados puedan ejecutarlo en los entornos habilitados para tal efecto.

## Estructura del proyecto

La estructura del proyecto consta de 8 grandes módulos:

- **agent**:     Agente AI en langchain.
- **ui**:        Interfaz de Usuario en Streamlit.
- **knowledge**: Conocimiento de estructura de la base de datos (MIMIC-IV)
- **output**:    Carpeta de salida para la monitorización de la Tool y de la carga de conocimiento en Qdrant.
- **scripts:**   Scripts de utilidad para el proyecto.
- **results:**   Lógica de evaluación de resultados y resultados obtenidos en formato 'json'.
- **notebooks:** Validaciones, experimento y resultados.
- **qdrant**:    docker-compose para desplegar base de datos vectorial.

El despliegue completo se detalla a continuación:

```
app/
|
|   (AI Agent Langchain)
|-- agent/
│   |-- __init__.py
│   |-- loader.py                     -> Clase que regula la lógica de la Carga del Conocimiento a Qdrant.
│   |-- agent.py                      -> Clase principal de la configuración del Agente.
│   |-- memory.py                     -> Clase que regula la memoria del AI Agent (Memoria simple)
│   |-- retriever.py                  -> Clase que regula la técnica RAG.
│   |-- tools.py                      -> Funciones llamables por el AI Agent.
│   |-- experiment_log.py             -> Clase que regula la monitorización de las *tools* y la monitorización de la carga de conocimiento.
│   |-- prompt_templates.py           -> Clase que regula el prompt base del agente.
│   |-- utils/                        -> Funciones auxiliares de utilidad para el AI Agent
|       |-- logging_config.py             -> Centralización del formato del logger.
|
|   (Interfaz Usuario Streamlit)
|-- ui/
|   |-- chat.py                       -> Página principal de la interfaz con la lógica del chat y llamada al AI Agent.
|   |-- utils/                        -> Contiene funciones auxiliares para la interfaz
|   |   |-- style.py                      -> Módulos de interfaz reutilizables.
|   |   |-- logs_sql.py                   -> Funciones para manejar los logs de SQL.
|   |   |-- metrics.py                    -> Módulos de cálculos de métricas y gráficos.
|   |-- auth/                         -> Contiene módulo de autenticación con AWS Cognito
|   |   |-- auth.py                       -> Lógica de autenticación.
|   |   |-- auth_decorators.py            -> Decorador, que permite modularizar la llamada a auth.py
|   |-- pages/                        -> Contiene las páginas secundarias de la app.
|   |   |-- 1_metrics.py                  -> Métricas de uso de las invocaciones a la Tool.
|   |   |-- 2_knowledge.py                -> Contiene la documentación de la base de datos cargada en Qdrant.
|   |   |-- 3_architecture.py             -> Contiene la arquitectura de la app.
|   |   |-- 4_logs_sql.py                 -> Visualización de los logs de SQL generados por todos los usuarios.
|   |-- static/                           -> Directorio con elementos estáticos: imágenes u otros archivos.
|
|   (Directorio de configuración de streamlit)
|-- .streamlit/                       
|      |-- config.toml                -> Archivo de configuración streamlit.
|
|   (Conocimiento estructura Base de Datos)
|-- knowledge/                         -> Módulo de conocimiento sobre la base datos (Archivos `.json`)
│   |-- schema.json                       -> `.json` estándar con el conocimiento para subir a Qdrant
│   |-- documentation/                    -> Módulo con `.json` de información cualitativa sobre la base de datos de interés.
|       |-- module_ed/                       -> `.json` del módulo de urgencias (información sobre tablas y campos).
|       |   |-- diagnosis.json               -> Tabla `diagnosis`: Diagnóstico facturado al alta del paciente.
|       |   |-- edstays.json                 -> Tabla `edstays`: Estancias Urgencias (principal) 
|       |   |-- medrecon.json                -> Tabla `medrecon`: Conciliación Medicamentos.
|       |   |-- triage.json                  -> Tabla `triage`: Información sobre el evento de Triaje.
|       |   |-- vitalsign.json               -> Tabla `vitalsign`: Toma de constantes vitales durante la estancia.
|       |   |-- pyxis.json                   -> Tabla `pyxis`: Dispensación de medicamentos.
|       |-- modules.json                  -> Información cualitativa sobre los módulos de MIMIC-IV
| 
|   (Resultados Experimento y Monitorización)
|-- output/
│   |-- Se ubican todos los archivos `.json` 
|       con la monitorización de los experimentos y la carga del esquema a Qdrant
|
|   (Scripts auxiliares)
|-- scripts/
│   |-- load_schema.py                -> Script para la carga de información `<prefijo_del_módulo>_schema.json`
|                                        en base de datos vectorial Qdrant.
│ 
|-- results/:                          -> Contiene scripts, csv y json referente a los resultados del experimento
|   |-- result_generator.py               -> Script para generar los resultados de la AI Tool vs dataset control
|   |-- evaluator.py                      -> Cálculo métricas de resultados.
|   |-- csv/                              -> Directorio salida csv generado por la evaluación de resultados.
|   |   |-- benchmark/                       -> Ubicación del dataset de control. MIMICEL, si decides replicar 
|   |   |                                       el experimento
|   |   |-- AI_Tool/                         -> Ubicación del dataset resultante tras ejecutar un script SQL 
|   |                                           exitosamente durante la evaluación.
|   |-- json/                                -> Directorio de salida con los archivos 'json' de resultados
|                                               del experimento en la replicación de dataset de control.
|
|-- notebooks/:                        -> Directorio que contiene notebooks referentes al experimento.
|   |-- Estructura_MIMICEL.ipynb          -> Verificación carga módulo ED MIMIC-IV en Postgres 16.8.
|   |                                        Y verificación dataset de control MIMICEL.
|   |-- N50_Experiment_Agent.ipynb        -> Lanzamiento del experimento, 50 invocaciones a AI Agent.
|   |-- Results.ipynb                     -> Resultados del experimento.
|
|-- (Qdrant)
|   qdrant/                            -> Módulo docker-compose para Qdrant (Base de Datos Vectorial)
|        |-- docker-compose.yml           -> Configuración docker-compose para Qdrant. 
│   
|-- README.md
|-- LICENSE.md
```

## Configuración del Entorno de Desarrollo

### 1. Creación del Entorno Virtual y Archivo Variables de Entorno ".env"

Es necesario crear un entorno virtual dentro del directorio raíz del proyecto:

1. Navega al directorio del proyecto:
```bash
cd /ruta/al/proyecto
```

2. Crea un archivo ".env" a partir de ".env.sample"


3. Crea el entorno virtual:
```bash
python -m venv venv
```

4. Activa el entorno virtual:

En Linux:
```bash
source venv/bin/activate
```

En Windows:
```bash
.\venv\Scripts\activate
```

5. Instala las dependencias:
```bash
pip install -r requirements.txt
```

6. Para desactivar el entorno virtual cuando hayas terminado:
```bash
deactivate
```

Nota: Asegúrate de que el directorio `venv` esté incluido en tu `.gitignore` para no subirlo al repositorio.

### 2. Instalación de Dependencias

Para la ejecución de este proyecto, **es necesaria una versión de Python:**

- **Python 3.12.3 o superior**

El archivo `requirements.txt` incluye las siguientes librerías con sus versiones específicas:

```txt
streamlit==1.45.0
boto3==1.38.8
openai==1.77.0
langchain==0.3.25
qdrant-client==1.14.2
python-dotenv==1.1.0
langchain-openai==0.3.16
langchain-core==0.3.58
PyJWT==2.10.1
plotly==6.0.1
kaleido==0.2.1
cryptography==44.0.3
scipy==1.15.3
numpy==2.2.5
pandas==2.2.3
scikit-learn==1.6.1
SQLAlchemy==2.0.40
psycopg2-binary==2.9.10
```

### 3. Configuración de Qdrant

Para instalar y ejecutar Qdrant utilizando Docker Compose:

1. **Requisitos previos**: 
   - Docker instalado ([guía de instalación](https://docs.docker.com/get-docker/))
   - Docker Compose instalado ([guía de instalación](https://docs.docker.com/compose/install/))

2. **Iniciar Qdrant**:
   ```bash
   cd qdrant
   docker-compose up -d
   ```

3. **Verificar el estado**:
   ```bash
   docker-compose ps
   ```

4. **Detener Qdrant**:
   ```bash
   docker-compose down
   ```

### 4. Carga del Esquema en Qdrant

Para cargar el esquema `ed_schema.json` ubicado en `knowledge` es necesario:

1. **Activa el entorno virtual desde la raíz del proyecto** (si no está activado):

```bash
source venv/bin/activate  # En Linux
.\venv\Scripts\activate  # En Windows

python -m scripts.load_schema
```

### 5. Ejecución de la Aplicación Chat AI Evento Log Generator (con interfaz de usuario)

1. **Activa el entorno virtual desde la raíz del proyecto** (si no está activado):

```bash
source venv/bin/activate  # En Linux
.\venv\Scripts\activate  # En Windows
```

2. **Inicia la aplicación Streamlit**:

```bash
streamlit run ui/chat.py # En Linux
streamlit run ui\chat.py # En Windows
```

3. **Accede a la aplicación** a través de tu navegador web en la URL que Streamlit proporciona (por defecto http://localhost:8501).

### 6. ¿Te interesa monitorizar los resultados de la herramienta de 'search_and_generate_sql' del AI Agent?

1. **Configura la variable de entorno a "DATA_EXPERIMENT" A "YES"**:

```python
# En archivo .env

DATA_EXPERIMENT = YES
```

2. **Interactúa con el agente:**

- Mediante la interfaz de usuario (Streamlit) usa el módulo de chat.
- Mediante Notebook.

**Mediante Notebook:**
```python
#¡Ojo! Dependiendo desde donde se ejecute el Notebook, es posible
# que sea necesario ajustar la ruta principal del proyecto con
# la librería 'Path'
from agent.agent import Agent

# Creación instancia del AI Agent
agent = Agent()

# Enviar "hola" al agente y capturar una respuesta
respuesta = agent.chat("hola")

# Elimine el historial
agent = agent.clear()
# O si lo prefieres
# Vuelve a generar una nueva instacia del AI Agent
agent = Agent()
```
**3. Monitorización métricas de rendimiento general:**

Hayas interactuado mediante interfaz, consola o notebook, si la variable de entorno DATA_EXPERIMENT está configurada, se generarán en el directorio **output/** los archivos "**TestToolAgent_<uuid>.json**". Se generaran tantos como Scripts SQL genere la herramienta "**search_and_generate_sql**".

Estos archivos, monitorizan principalmente el rendimiento en tiempo de ejecución, tokens consumidos y coste en USD totales y por cada uno de los componentes de la herramienta.

**4. Monitorización métricas de calidad reconstrucción log de eventos de control:**

Si te interesa monitorizar la **calidad de la reconstrucción de un dataset de control**, es necesario que:

 - Existan ficheros **'TestToolAgent_<uuid>.json'** en directorio **'output/'** mediante invocaciones previas al AI Agent.  
 - El entorno virtual del proyecto esté activado, con la versión de Python y las librerías necesarias instaladas. (Leer el README.md)  
 - El fichero del dataset de control, **en nuestro caso 'mimicel.csv'**, se encuentre en **'results/csv/benchmark'**  
 - Si quieres personalizar alguna ruta, puedes hacerlo en la función main():  
     log_json_path:    ruta al archivo o los archivos json que se generó al trackear la AI Tool,
                       se ubican en el proyecto en la carpeta output (output/TestToolAgent_<uuid>.json)
     df_benchmark:     pandas dataframe con el benchmark.
     ai_csv_dir:       ruta a la carpeta donde se guardan los csv generados por la AI Tool.
     results_json_dir: ruta a la carpeta donde se guardan los json con los resultados de la evaluación.

**Por consola, desde la raíz del proyecto, invoca directamente al script:**

```bash
python -m results.result_generator
```
Si se han generado ficheros de resultados, se guardarán en **'results/json/Result_<TestToolAgent_(uuid)>.json'**

Estos archivos monitorizan principalmente la calidad de la reconstrucción del dataset de control.
(Ver lógica y métricas en: **'results/result_generator.py'** y **'results/evaluator.py'**)

## Licencia

Este proyecto está licenciado bajo la Licencia Apache 2.0 - ver el archivo [LICENSE.md](LICENSE.md) para más detalles.

