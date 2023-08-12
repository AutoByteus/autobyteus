# File: src/llm_integrations/openai_integration/openai_api_factory.py

"""
openai_api_factory.py: Implements the OpenAIApiFactory class.
This class is responsible for creating instances of the OpenAI API classes based on the provided type.
"""

from src.llm_integrations.openai_integration.base_openai_api import BaseOpenAIApi
from src.llm_integrations.openai_integration.openai_chat_api import OpenAIChatApi

class OpenAIApiFactory:
    """
    OpenAIApiFactory is a class responsible for creating instances of the OpenAI API classes based on the provided type.
    """

    @staticmethod
    def create_api(api_type: str) -> BaseOpenAIApi:
        """
        Create an instance of an OpenAI API class based on the provided type.

        :param api_type: The type of the OpenAI API class to create an instance of.
        :type api_type: str
        :return: An instance of an OpenAI API class.
        :rtype: BaseOpenAIApi
        """
        
        if api_type == 'chat':
            return OpenAIChatApi()
        else:
            raise ValueError(f"Invalid API type: {api_type}. Valid types are 'chat' and 'completion'.")
