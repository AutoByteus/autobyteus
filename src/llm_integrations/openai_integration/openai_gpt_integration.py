# File: src/llm_integrations/openai_integration/openai_gpt_integration.py

"""
openai_gpt_integration.py: Implements the OpenAIGPTIntegration class which extends the BaseLLMIntegration abstract base class.
This class integrates the OpenAI GPT models (gpt3.5-turbo, gpt4) with the agent program. It uses the OpenAI API to process a list of input messages and return the model's responses.
"""

from src.config import config
from .openai_api_factory import OpenAI_API_Factory
from src.llm_integrations.base_llm_integration import BaseLLMIntegration


class OpenAIGPTIntegration(BaseLLMIntegration):
    """
    OpenAIGPTIntegration is a concrete class that extends the BaseLLMIntegration class.
    This class is responsible for processing input messages and returning responses from the OpenAI GPT model.
    """

    def __init__(self, api_type):
        super().__init__()
        self.api = OpenAI_API_Factory.create_api(api_type)

    async def process_input_messages(self, input_messages):
        """
        Process a list of input messages and return the LLM's responses.

        :param input_messages: List of input messages to be processed.
        :type input_messages: list
        :return: List of responses from the OpenAI GPT model
        :rtype: list
        """
        return self.api.process_input_messages(input_messages)
