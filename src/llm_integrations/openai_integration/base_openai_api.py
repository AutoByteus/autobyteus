# File: src/llm_integrations/openai_integration/base_openai_api.py

"""
base_openai_api.py: Defines the BaseOpenAI_API abstract base class.
This class provides an interface for interacting with the OpenAI API.
"""

from abc import ABC, abstractmethod


class BaseOpenAIApi(ABC):
    """
    BaseOpenAI_API is an abstract base class that provides an interface for interacting with the OpenAI API.
    """

    @abstractmethod
    def process_input_messages(self, input_messages):
        """
        Process a list of input messages and return the responses.

        :param input_messages: List of input messages to be processed.
        :type input_messages: list
        :return: List of responses
        :rtype: list
        """
        pass
