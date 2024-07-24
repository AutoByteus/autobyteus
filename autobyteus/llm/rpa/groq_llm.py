from enum import Enum
from autobyteus.llm.base_llm import BaseLLM
from llm_ui_integration.ui_integrators.groq_ui_integrator.groq_ui_integrator import GroqUIIntegrator

class GroqModel(Enum):
    GEMMA_2_9B_IT = "gemma2-9b-it"
    GEMMA_7B_IT = "gemma-7b-it"
    LLAMA_3_1_405B_REASONING = "llama-3-1-405b-reasoning"
    LLAMA_3_1_70B_VERSATILE = "llama-3-1-70b-versatile"
    LLAMA_3_1_8B_INSTANT = "llama-3-1-8b-instant"
    LLAMA3_70B_8192 = "llama3-70b-8192"
    LLAMA3_8B_8192 = "llama3-8b-8192"
    MIXTRAL_8X7B_32768 = "mixtral-8x7b-32768"

class GroqLLM(BaseLLM):
    def __init__(self, model: GroqModel):
        """
        Initialize the GroqLLM instance.

        :param model: The Groq model to use.
        :type model: GroqModel
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