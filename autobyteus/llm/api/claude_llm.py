from typing import Optional, List
import anthropic
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message

class ClaudeLLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.client = self.initialize()
        self.model = model_name.value if model_name else "claude-3-5-sonnet-20240620"
        self.system_message = system_message or "You are a helpful assistant."
        self.messages = []
        super().__init__(model=self.model)

    @classmethod
    def initialize(cls):
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            return anthropic.Anthropic(api_key=anthropic_api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0,
                system=self.system_message,
                messages=[msg.to_dict() for msg in self.messages]
            )

            assistant_message = response.content[0].text
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except anthropic.APIError as e:
            raise ValueError(f"Error in Claude API call: {str(e)}")

    async def cleanup(self):
        pass