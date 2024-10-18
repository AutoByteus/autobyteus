# mistral_chat_api.py
import os
from mistralai import Mistral, UserMessage, AssistantMessage
from typing import Optional, List

from autobyteus.llm.api.base_chat import BaseChatAPI, Message, MessageRole

class MistralChat(BaseChatAPI):
    default_model = "mistral-large-latest"

    @classmethod
    def initialize(cls):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not set")
        return Mistral(api_key=api_key)

    def _convert_to_mistral_message(self, message: Message):
        if message.role == MessageRole.USER:
            return UserMessage(content=message.content)
        return AssistantMessage(content=message.content)

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        mistral_messages = [self._convert_to_mistral_message(msg) for msg in self.messages]
        chat_response = self.client.chat.complete(
            model=self.model,
            messages=mistral_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        assistant_message = chat_response.choices[0].message.content
        self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
        return assistant_message

    async def cleanup(self):
        pass