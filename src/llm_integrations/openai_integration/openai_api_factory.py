"""
openai_api_factory.py: Implements the OpenAIApiFactory class.
This class is responsible for creating instances of the OpenAI API classes based on the provided type.
"""

from src.llm_integrations.openai_integration.base_openai_api import ApiType, BaseOpenAIApi
from src.llm_integrations.openai_integration.openai_chat_api import OpenAIChatApi

class OpenAIApiFactory:
    """
    OpenAIApiFactory is a class responsible for creating instances of the OpenAI API classes based on the provided type.
    """

    @staticmethod
    def create_api(api_type: ApiType = ApiType.CHAT, model_name: str = None) -> BaseOpenAIApi:
        """
        Create an instance of an OpenAI API class based on the provided type and model name.

        :param api_type: The type of the OpenAI API class to create an instance of.
        :type api_type: ApiType, optional, default to ApiType.CHAT
        :param model_name: Name of the OpenAI model to be used. If not provided, the default from the OpenAIChatApi class will be used.
        :type model_name: str, optional
        :return: An instance of an OpenAI API class.
        :rtype: BaseOpenAIApi
        """
        if api_type == ApiType.CHAT:
            return OpenAIChatApi(model_name=model_name)
        else:
            raise ValueError(f"Invalid API type: {api_type}. Valid types are {', '.join([api.name for api in ApiType])}.")
