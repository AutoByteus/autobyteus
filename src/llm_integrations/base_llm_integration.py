"""
base_llm_integration.py: Contains the BaseLLMIntegration abstract base class for Language Model integrations.
The BaseLLMIntegration class now supports an optional project configuration (a dictionary) as an attribute.
"""

from abc import ABC, abstractmethod


class BaseLLMIntegration(ABC):
    """
    BaseLLMIntegration is an abstract base class that defines the common interface for all LLM integrations.
    It now includes an optional config attribute for providing project configurations.
    """
    
    @abstractmethod
    def process_input_messages(self, input_messages):
        """
        Process a list of input messages and return the LLM's responses.

        :param input_messages: List of input messages to be processed.
        :type input_messages: list
        """
        pass
