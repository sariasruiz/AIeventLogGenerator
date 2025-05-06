###############################################
# memory.py
###############################################

from typing import List, Dict, Any
from pydantic import PrivateAttr
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.memory import BaseMemory

import logging
from agent.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

#  ChatHistory: Historial completo de mensajes
class ChatHistory(BaseChatMessageHistory):
    """
    Historial de mensajes en memoria siguiendo documentación oficial de LangChain.
    - Usado para guardar e interactuar con el historial de mensajes del chat
    Link a documentación oficial:
    https://python.langchain.com/api_reference/core/chat_history/langchain_core.chat_history.BaseChatMessageHistory.html#langchain_core.chat_history.BaseChatMessageHistory
    """

    def __init__(self) -> None:
        self.messages: List[BaseMessage] = []

    # API BaseChatMessageHistory
    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(message)

    def add_user_message(self, content: str) -> None:
        self.add_message(HumanMessage(content=content))

    def add_ai_message(self, content: str) -> None:
        self.add_message(AIMessage(content=content))
    
    def get_messages(self) -> List[BaseMessage]:
        return self.messages

    def clear(self) -> None:
        self.messages = []



# SimpleMemory: Convierte ChatHistory en un BaseMemory
class SimpleMemory(BaseMemory):
    """
    Memoria conversacional simple basada en ChatHistory siguiendo
    documentación oficial de LangChain.
    """
    # Atributo privado para guardar el historial
    _history: ChatHistory = PrivateAttr()

    def __init__(self, history: ChatHistory):
        """
        Argumentos:
            history (ChatHistory): Instancia compartida que guarda mensajes.
        """
        super().__init__() # llamada al constructor de la clase padre, para usar atributo privado
        self._history = history

    @property
    def memory_variables(self) -> List[str]:
        """
        Claves disponibles como memoria para el agente.
        """
        return ["chat_history"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, List[BaseMessage]]:
        """
        Devuelve el historial como string formateado para el prompt del agente.
        """
        messages = self._history.get_messages()
        return {"chat_history": messages}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Guarda en memoria el mensaje del usuario y la respuesta del asistente.
        """
        try:
            user_msg = inputs.get("input", "")
            ai_msg = outputs.get("output", "")
            self._history.add_user_message(user_msg)
            self._history.add_ai_message(ai_msg)
        except Exception as e:
            logger.exception("Error al guardar contexto en memoria.")

    def clear(self) -> None:
        """
        Limpia todo el historial de memoria.
        """
        self._history.clear()
        logger.info("Memoria limpiada.")