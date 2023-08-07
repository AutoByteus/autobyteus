# File: src/llm_integrations/openai_integration/openai_chat_api.py

"""
openai_chat_api.py: Implements the OpenAI_Chat_API class which extends the BaseOpenAI_API abstract base class.
This class is responsible for processing input messages and returning responses using the OpenAI Chat API.
"""

import openai
from src.config import config
from src.llm_integrations.openai_integration.base_openai_api import BaseOpenAIApi


class OpenAIChatApi(BaseOpenAIApi):
    """
    OpenAI_Chat_API is a concrete class that extends the BaseOpenAI_API class.
    This class is responsible for processing input messages and returning responses using the OpenAI Chat API.
    """

    def __init__(self):
        self.model = config.get('OPEN_AI_MODEL', 'gpt-3.5-turbo')  # default model is gpt-3.5-turbo

    def process_input_messages(self, input_messages):
        """
        Process a list of input messages and return the responses using the OpenAI Chat API.

        :param input_messages: List of input messages to be processed.
        :type input_messages: list
        :return: List of responses from the OpenAI Chat API
        :rtype: list
        """
        responses = []
        for message in input_messages:
            chat_messages = [{"role": "user", "content": message}]
            chat_completion = openai.ChatCompletion.create(model=self.model, messages=chat_messages)
            responses.append(chat_completion.choices[0].message.content)
        return responses
