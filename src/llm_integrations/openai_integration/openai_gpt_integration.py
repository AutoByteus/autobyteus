"""
openai_gpt_integration.py: Implements the OpenAIGPTIntegration class which extends the BaseLLMIntegration abstract base class.
This class integrates the OpenAI GPT models (gpt3.5-turbo, gpt4) with the agent program. It uses the OpenAI API to process a list of input messages and return the model's responses.
"""

from typing import List
from src.config import config
from src.llm_integrations.openai_integration.base_openai_api import BaseOpenAIApi
from src.llm_integrations.openai_integration.openai_api_factory import ApiType, OpenAIApiFactory
from src.llm_integrations.base_llm_integration import BaseLLMIntegration
from src.llm_integrations.openai_integration.openai_message_types import SystemMessage, UserMessage
from src.llm_integrations.openai_integration.openai_models import OpenAIModel

class OpenAIGPTIntegration(BaseLLMIntegration):
    """
    OpenAIGPTIntegration is a concrete class that extends the BaseLLMIntegration class.
    This class is responsible for processing input messages and returning responses from the OpenAI GPT model.
    
    :param api_type: Type of the OpenAI API to use.
    :type api_type: ApiType
    :param model_name: Name of the OpenAI model to be used. If not provided, the default from the respective API class will be used.
    :type model_name: OpenAIModel, optional
    """

    def __init__(self, api_type: ApiType = ApiType.CHAT, model_name: OpenAIModel = None):
        super().__init__()
        if model_name:
            self.openai_api: BaseOpenAIApi = OpenAIApiFactory.create_api(api_type, model_name)
        else:
            self.openai_api: BaseOpenAIApi = OpenAIApiFactory.create_api(api_type)
    
    def process_input_messages(self, input_messages: List[str]) -> str:
        """
        Process a list of input messages and return the LLM's response content.

        :param input_messages: List of input messages to be processed.
        :type input_messages: List[str]
        :return: Response content from the OpenAI GPT model.
        :rtype: str
        """
        # Create SystemMessage
        system_message = SystemMessage("You are ChatGPT, a large language model trained by OpenAI, based on the GPT-3.5 architecture. Knowledge cutoff: September 2021. Please feel free to ask me anything.")
        
        # Convert each message in the input_messages to a UserMessage
        user_messages = [UserMessage(message) for message in input_messages]
        
        # Construct the messages list
        messages = [system_message] + user_messages
        
        # Process the messages using the API and get the response
        response = self.openai_api.process_input_messages(messages)
        
        return response.content