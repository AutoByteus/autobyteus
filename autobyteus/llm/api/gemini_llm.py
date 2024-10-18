# gemini_chat_api.py
import os
import google.generativeai as genai
from typing import Optional, List

from autobyteus.llm.api.base_chat import BaseChatAPI, Message, MessageRole
from autobyteus.llm.utils.llm_config import LLMConfig

class GeminiChat(BaseChatAPI):
    default_model = "gemini-1.5-flash"

    def __init__(self, model_name=None, system_message: str = None, custom_config: LLMConfig = None):
        super().__init__(model_name, system_message, custom_config)
        self.chat_session = None

    @classmethod
    def initialize(cls):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=api_key)
        return genai

    def _ensure_chat_session(self):
        if not self.chat_session:
            model = self.client.GenerativeModel(
                model_name=self.model,
                generation_config={
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p or 0.95,
                    "max_output_tokens": self.config.max_tokens or 8192,
                }
            )
            history = [{"role": msg.role.value, "parts": [msg.content]} for msg in self.messages]
            self.chat_session = model.start_chat(history=history)

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        self._ensure_chat_session()
        response = self.chat_session.send_message(user_message)
        assistant_message = response.text
        self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
        return assistant_message

    async def cleanup(self):
        self.chat_session = None