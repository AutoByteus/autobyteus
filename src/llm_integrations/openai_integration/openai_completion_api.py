# File: src/llm_integrations/openai_integration/openai_completion_api.py

"""
openai_completion_api.py: Implements the OpenAI_Completion_API class which extends the BaseOpenAI_API abstract base class.
This class is responsible for processing input messages and returning responses using the OpenAI Completion API.
"""

import openai
from src.config import config
from src.llm_integrations.openai_integration.base_openai_api import BaseOpenAIApi


class OpenAiCompletionApi(BaseOpenAIApi):
    """
    OpenAI_Completion_API is a concrete class that extends the BaseOpenAI_API class.
    This class is responsible for processing input messages and returning responses using the OpenAI Completion API.
    """

    def __init__(self):
        self.model = config.get('OPEN_AI_MODEL', 'gpt-3.5-turbo')  # default model is gpt-3.5-turbo

    def process_input_messages(self, input_messages):
        """
        Process a list of input messages and return the responses using the OpenAI Completion API.

        :param input_messages: List of input messages to be processed.
        :type input_messages: list
        :return: List of responses from the OpenAI Completion API
        :rtype: list
        """
        responses = []
        for message in input_messages:
            completion = openai.Completion.create(engine=self.model, prompt=message)
            responses.append(completion.choices[0].text.strip())
        return responses
