"""
openai_gpt_integration.py: Implements the OpenAIGPTIntegration class which extends the BaseLLMIntegration abstract base class.
This class integrates the OpenAI GPT models (gpt3.5-turbo, gpt4) with the agent program. It uses the OpenAI API to process a list of input messages and return the model's responses.
"""

from src.config import config
from src.llm_integrations.openai_integration.base_openai_api import BaseOpenAIApi
from src.llm_integrations.openai_integration.openai_api_factory import ApiType, OpenAIApiFactory
from src.llm_integrations.base_llm_integration import BaseLLMIntegration

class OpenAIGPTIntegration(BaseLLMIntegration):
    """
    OpenAIGPTIntegration is a concrete class that extends the BaseLLMIntegration class.
    This class is responsible for processing input messages and returning responses from the OpenAI GPT model.
    
    :param api_type: Type of the OpenAI API to use.
    :type api_type: ApiType
    :param model_name: Name of the OpenAI model to be used. If not provided, the default from the respective API class will be used.
    :type model_name: str, optional
    """

    def __init__(self, api_type: ApiType = ApiType.CHAT, model_name: str = None):
        super().__init__()
        self.openai_api: BaseOpenAIApi = OpenAIApiFactory.create_api(api_type, model_name)

    def process_input_messages(self, input_messages):
        """
        Process a list of input messages and return the LLM's responses.

        :param input_messages: List of input messages to be processed.
        :type input_messages: list
        :return: List of responses from the OpenAI GPT model
        :rtype: list
        """

        return self.openai_api.process_input_messages(input_messages)  # We're now processing one message at a time
