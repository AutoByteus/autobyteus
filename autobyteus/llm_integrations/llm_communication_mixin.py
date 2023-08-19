"""
Module: llm_communication_mixin

This module provides the LLMCommunicationMixin, a mixin class that facilitates communication
with the LLM system by constructing prompts, sending them, and processing the LLM's responses.
"""

from abc import ABC, abstractmethod

class LLMCommunicationMixin(ABC):
    """
    LLMCommunicationMixin encapsulates the logic to interact with the LLM system.
    
    Classes using this mixin can easily construct prompts, send them to LLM, 
    and process the LLM's responses.
    """
    prompt_template = None

    @abstractmethod
    def construct_prompt(self) -> str:
        """
        Construct the prompt based on the prompt_template. This should be implemented
        by subclasses to provide specific prompt construction logic.

        Returns:
            str: The constructed prompt.
        """
        pass

    async def send_to_llm(self, prompt: str) -> str:
        """
        Send the constructed prompt to LLM and retrieve the response.

        Args:
            prompt (str): The constructed prompt to be sent.

        Returns:
            str: The response from LLM.
        """
        # Use BaseLLMIntegration or any specific integration to send the prompt
        response = await self.llm_integration.process_input_messages([prompt])
        return response

    def process_response(self, response: str):
        """
        Process the response from the LLM. This can be overridden by subclasses if needed.

        Args:
            response (str): The response from LLM.
        """
        pass
