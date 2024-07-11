from autobyteus.llm.base_llm import BaseLLM
from llm_ui_integration.ui_integrators.claude_ui_integrator.claude_ui_integrator import ClaudeUIIntegrator
from llm_ui_integration.ui_integrators.claude_ui_integrator.claude_models import ClaudeModel


class ClaudeChatLLM(BaseLLM):
    def __init__(self, model: ClaudeModel):
        self.ui_integrator = ClaudeUIIntegrator(model=model)
        

    async def send_user_message(self, user_message, **kwargs):
        """
        send a user message and return the LLM's response.

        :param user_message: The user message to be processed.
        :type user_message: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        """
        user_message_index = kwargs.get("user_message_index")
        if user_message_index is None:
            raise ValueError("user_message_index is required in kwargs")
        
        response = await self.ui_integrator.send_user_message(user_message, user_message_index)
        return response
