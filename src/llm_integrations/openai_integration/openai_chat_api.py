"""
openai_chat_api.py: Implements the OpenAIChatApi class which extends the BaseOpenAIApi abstract base class.
This class is responsible for processing a list of message interactions and returning a response using the OpenAI Chat API.
"""

from src.llm_integrations.openai_integration.base_openai_api import BaseOpenAIApi
from src.config import config
import openai

class OpenAIChatApi(BaseOpenAIApi):
    """
    OpenAIChatApi is a concrete class that extends the BaseOpenAIApi class.
    This class processes a series of message interactions and fetches a response using the OpenAI Chat API.
    
    :param model_name: Name of the OpenAI model to be used. Defaults to 'gpt-3.5-turbo' or the value from the config.
    :type model_name: str
    """

    def __init__(self, model_name: str = None):
        self.initialize()  # Ensure OpenAI is initialized
        # Use provided model name or default from the config
        self.model = model_name or config.get('OPEN_AI_MODEL', 'gpt-3.5-turbo')  

    def process_input_messages(self, messages: list) -> str:
        """
        Process a list of message interactions and return the response using the OpenAI Chat API.

        :param messages: A list of message interactions to be processed.
        :type messages: list of dicts (e.g., [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Who won the world cup in 2018?"}])
        :return: Response content from the OpenAI Chat API.
        :rtype: str
        """
        response = openai.ChatCompletion.create(model=self.model, messages=messages)
        return response['choices'][0]['message']['content']
