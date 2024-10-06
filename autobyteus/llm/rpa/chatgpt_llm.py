from typing import List, Optional
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.models import LLMModel
from llm_ui_integration.ui_integrators.chatgpt_ui_integrator.chatgpt_ui_integrator import ChatGPTUIIntegrator

class ChatGPTLLM(BaseLLM):
    def __init__(self, model: LLMModel, custom_config: LLMConfig = None):
        super().__init__(model, custom_config)
        self.ui_integrator = ChatGPTUIIntegrator(model.value)

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs):
        """
        Send a user message and return the LLM's response.

        :param user_message: The user message to be processed.
        :type user_message: str
        :param file_paths: Optional list of file paths to be sent with the message.
        :type file_paths: Optional[List[str]]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The LLM's response to the user message.
        :rtype: str
        :raises ValueError: If user_message_index is not provided in kwargs.
        """
        user_message_index = kwargs.get("user_message_index")
        if user_message_index is None:
            raise ValueError("user_message_index is required in kwargs")
        
        response = await self.ui_integrator.send_user_message(user_message, file_paths, user_message_index)
        return response
    
    async def cleanup(self):
        """
        Clean up resources used by the ChatGPT LLM.
        """
        await self.ui_integrator.close()

