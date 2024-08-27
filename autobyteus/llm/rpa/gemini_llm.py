# file: autobyteus/llm/rpa/gemini_llm.py
from autobyteus.llm.base_llm import BaseLLM
from llm_ui_integration.ui_integrators.gemini_studio_ui_integrator.gemini_studio_ui_integrator import GeminiStudioUIIntegrator

from autobyteus.llm.models import LLMModel

class GeminiLLM(BaseLLM):
    def __init__(self, model: LLMModel):
        """
        Initialize the GeminiLLM instance.

        :param model: The Gemini model to use.
        :type model: LLMModel
        """
        super().__init__()
        self.model = model
        self.ui_integrator = GeminiStudioUIIntegrator(model.value)

    async def send_user_message(self, user_message: str, **kwargs) -> str:
        """
        Send a user message and return the LLM's response.
        
        :param user_message: The user message to be processed.
        :type user_message: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The LLM's response to the user message.
        :rtype: str
        :raises ValueError: If user_message_index is not provided in kwargs.
        """
        user_message_index = kwargs.get("user_message_index")
        if user_message_index is None:
            raise ValueError("user_message_index is required in kwargs")
        
        response = await self.ui_integrator.send_user_message(user_message, user_message_index)
        return response
    
    async def cleanup(self):
        """
        Clean up resources used by the Gemini LLM.
        """
        await self.ui_integrator.close()