"""
llm_registry.py

This module provides a registry for storing and managing LLM integrations.

LLM integrations are stored in a dictionary, with the name of the LLM model as the key,
and the corresponding LLM integration object as the value.
"""

from typing import Dict, Optional
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.openai.openai_gpt_integration import OpenAIGPTIntegration
from autobyteus.llm.openai.openai_models import OpenAIModel
from autobyteus.config import config
from autobyteus.utils.singleton import SingletonMeta
# Import other LLM integrations as needed

class LLMRegistry(metaclass=SingletonMeta):
    """
    A registry to store and manage LLM integrations.

    Attributes:
        registry (Dict[str, BaseLLM]): A dictionary mapping LLM model names to
            their corresponding LLM integration.
    """

    def __init__(self):
        """
        Initialize LLMRegistry.

        All supported LLM integrations are created and registered in the constructor.
        """
        self.registry: Dict[str, BaseLLM] = {
            OpenAIModel.GPT_3_5_TURBO: OpenAIGPTIntegration(model_name=OpenAIModel.GPT_3_5_TURBO),
            OpenAIModel.GPT_4: OpenAIGPTIntegration(model_name=OpenAIModel.GPT_4),
            # Add other LLM integrations as needed
        }

    def add(self, model_name: str, integration: BaseLLM) -> None:
        """
        Adds an LLM integration to the registry.

        Args:
            model_name (str): The name of the LLM model.
            integration (BaseLLM): The LLM integration to be added.
        """
        self.registry[model_name] = integration

    def get(self, model_name: str) -> Optional[BaseLLM]:
        """
        Retrieves an LLM integration from the registry.

        Args:
            model_name (str): The name of the LLM model.

        Returns:
            Optional[BaseLLM]: The LLM integration if it exists, None otherwise.
        """
        return self.registry.get(model_name)

    def exists(self, model_name: str) -> bool:
        """
        Checks if an LLM integration already exists in the registry.

        Args:
            model_name (str): The name of the LLM model.

        Returns:
            bool: True if the LLM integration exists, False otherwise.
        """
        return model_name in self.registry
