from autobyteus.llm.base_llm import BaseLLM
from llm_ui_integration.ui_integrators.gemini_ui_integrator.gemini_ui_integrator import GeminiUIIntegrator

class GeminiLLM(BaseLLM):
    def __init__(self):
        """
        Initialize the GeminiLLM instance.
        """
        self.ui_integrator = GeminiUIIntegrator()

    async def send_user_message(self, user_message, **kwargs):
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