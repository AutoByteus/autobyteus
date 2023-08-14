# File: src/llm_integrations/openai_integration/base_openai_api.py

"""
base_openai_api.py: Provides an abstract base class for OpenAI API implementations.
This class offers common functionalities and enforces the structure for derived API classes.
"""
from enum import Enum, auto
from abc import ABC, abstractmethod
import openai
from src.config import config


class ApiType(Enum):
    CHAT = auto()
    
class BaseOpenAIApi(ABC):
    """
    An abstract base class offering common functionalities for OpenAI API implementations.
    Derived classes should implement the process_input_messages method.
    """
    _initialized = False

    @classmethod
    def initialize(cls):
        """
        Initialize the OpenAI API with the necessary configurations.
        This method ensures idempotent initialization.
        """
        if not cls._initialized:
            openai.api_key = config.get('OPENAI_API_KEY')
            cls._initialized = True

    @abstractmethod
    def process_input_messages(self, messages: list) -> str:
        """
        Abstract method to process a list of message interactions using the specific OpenAI API.

        :param messages: A list of message interactions to be processed.
        :type messages: list
        :return: Response from the specific OpenAI API.
        :rtype: str
        """
        pass
