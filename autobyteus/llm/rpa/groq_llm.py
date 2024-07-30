from autobyteus.llm.base_llm import BaseLLM
from llm_ui_integration.ui_integrators.groq_ui_integrator.groq_ui_integrator import GroqUIIntegrator
from autobyteus.llm.models import LLMModel

class GroqLLM(BaseLLM):
    def __init__(self, model: LLMModel):
        """
        Initialize the GroqLLM instance.

        :param model: The Groq model to use.
        :type model: LLMModel
        """
        self.ui_integrator = GroqUIIntegrator(model.value)

    async def send_user_message(self, user_message: str, **kwargs):
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

    async def start_new_conversation(self):
        """
        Start a new conversation with the Groq model.
        """
        await self.ui_integrator.start_new_conversation()

    async def close(self):
        """
        Close the UI integrator and clean up resources.
        """
        await self.ui_integrator.close()