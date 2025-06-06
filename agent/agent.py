###############################################
# agent.py
###############################################
import logging
import os
from typing import List, Dict
from dotenv import load_dotenv
import uuid

# LangChain core
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI

# Importaciones locales
from agent.retriever import QdrantRetriever
from agent.memory import ChatHistory
from agent.memory import SimpleMemory
from agent.prompt_templates import SchemaPromptTemplates
from agent.tools import search_and_generate_sql
from agent.utils.logging_config import setup_logging

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

class Agent:
    """Agente especializado en el esquema: búsqueda + generación de SQL para crear logs de eventos."""
    def __init__(self) -> None:
        # Configuración inicial
        self.id_experiment = uuid.uuid4()
        self.llm_provider = os.getenv("LLM_PROVIDER", "OPENAI").upper()
        self.llm_provider_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        # Una temperatura de 0 es para que el LLM sea determinista (lo menos creativo posible)
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", 0))
        logger.info("LLM: %s (%s, T=%s)", self.llm_model, self.llm_provider, self.llm_temperature)

        # Componentes del Agente
        # LLM
        self.llm = self._load_llm()

        # RAG
        self.retriever = QdrantRetriever()

        # Memoria
        self.chat_history = ChatHistory()
        self.memory = SimpleMemory(self.chat_history)

        # Lista de Tools disponibles para el agente
        # Esta lista se puede ampliar con otras herramientas, es la gracia del Tool Calling.
        tools = [
            search_and_generate_sql
        ]

        # Prompt Template
        prompt = SchemaPromptTemplates.get_base_template()

        # Agente y orquestador
        agent = create_tool_calling_agent(llm=self.llm, tools=tools, prompt=prompt)
        self.executor = AgentExecutor(agent=agent, tools=tools, memory=self.memory, verbose=True)


    #  Carga LLM del 
    def _load_llm(self):
        """
        Devuelve la instancia de LLM según el proveedor.
        """
        if self.llm_provider == "OPENAI":
            return ChatOpenAI(model=self.llm_model, temperature=self.llm_temperature)
        # Añadir futuros proveedores de LLM elif
        else:
            raise ValueError(f"Proveedor LLM todavía no soportado: {self.llm_provider}")

    #  Chat
    def chat(self, message: str) -> str:
        """Envía un mensaje al agente y devuelve la respuesta."""
        try:
            
            resp = self.executor.invoke({"input": message})["output"]
            
            return resp
        except Exception as exc:
            logger.error(f"Fallo al procesar mensaje: {exc}")
            return str(exc)


    #  Gestión Historial
    def history(self) -> List[Dict[str, str]]:
        """
        Devuelve el historial de mensajes relevantes para el modelo.
        """
        return self.memory.get_trimmed()

    def clear(self) -> None:
        """
        Resetea la memoria del agente.
        """
        self.memory.clear()
