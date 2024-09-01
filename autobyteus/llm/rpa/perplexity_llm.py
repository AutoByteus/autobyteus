from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.models import LLMModel
from llm_ui_integration.ui_integrators.perplexity_ui_integrator.perplexity_ui_integrator import PerplexityUIIntegrator

class PerplexityLLM(BaseLLM):
    def __init__(self, model: LLMModel, custom_config: LLMConfig = None):
        super().__init__(model, custom_config)
        self.ui_integrator = PerplexityUIIntegrator(model.value)

    async def _send_user_message_to_llm(self, user_message: str, **kwargs):
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
        Start a new conversation with the Perplexity model.
        """
        await self.ui_integrator.start_new_conversation()

    async def cleanup(self):
        """
        Close the UI integrator and clean up resources.
        """
        await self.ui_integrator.close()
