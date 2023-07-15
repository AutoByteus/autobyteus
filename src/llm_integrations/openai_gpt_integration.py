"""
openai_gpt_integration.py: Implements the OpenAIGPTIntegration class which extends the BaseLLMIntegration abstract base class.
This class integrates the OpenAI GPT models (gpt3.5-turbo, gpt4) with the agent program. It uses the OpenAI API to process a list of input messages and return the model's responses.
"""

import openai
from src.config import config
from src.llm_integrations.base_llm_integration import BaseLLMIntegration

class OpenAIGPTIntegration(BaseLLMIntegration):
    """
    OpenAIGPTIntegration is a concrete class that extends the BaseLLMIntegration class.
    This class is responsible for processing input messages and returning responses from the OpenAI GPT model.
    """

    def __init__(self):
        super().__init__()
        self.api_key = config.get('OPEN_AI_API_KEY')
        self.model = config.get('OPEN_AI_MODEL', 'gpt-3.5-turbo')  # default model is gpt-3.5-turbo

    async def process_input_messages(self, input_messages):
        """
        Process a list of input messages and return the LLM's responses.

        :param input_messages: List of input messages to be processed.
        :type input_messages: list
        :return: List of responses from the OpenAI GPT model
        :rtype: list
        """
        responses = []
        for message in input_messages:
            chat_messages = [{"role": "user", "content": message}]
            chat_completion = openai.ChatCompletion.create(model=self.model, messages=chat_messages)
            responses.append(chat_completion.choices[0].message.content)
        return responses
