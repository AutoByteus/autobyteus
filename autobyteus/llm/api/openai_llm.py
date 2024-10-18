# openai_chat_api.py
import os
import openai
from typing import Optional, List

from autobyteus.llm.api.base_chat import BaseChatAPI, Message, MessageRole

class OpenAIChat(BaseChatAPI):
    default_model = "gpt-3.5-turbo"

    @classmethod
    def initialize(cls):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        return openai.OpenAI(api_key=api_key)

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[msg.to_dict() for msg in self.messages],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            **self.config.extra_params
        )
        assistant_message = response.choices[0].message.content
        self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
        return assistant_message

    async def cleanup(self):
        pass