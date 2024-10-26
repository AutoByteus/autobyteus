from typing import Optional, List
import google.generativeai as genai
import os

import tiktoken
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message

class GeminiLLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.client = self.initialize()
        self.model = model_name.value if model_name else "gemini-1.5-flash"
        self.generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        self.chat_session = None
        self.messages = []
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Use a compatible tokenizer
        if system_message:
            # Instead of using MessageRole.SYSTEM, we'll use MessageRole.USER
            # and prepend "System:" to the message content
            self.messages.append(Message(MessageRole.USER, f"System: {system_message}"))
        super().__init__(model=self.model)

    @classmethod
    def initialize(cls):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            genai.configure(api_key=api_key)
            return genai
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini: {str(e)}")

    def _ensure_chat_session(self):
        if not self.chat_session:
            model = self.client.GenerativeModel(
                model_name=self.model,
                generation_config=self.generation_config
            )
            history = []
            for msg in self.messages:
                history.append({"role": msg.role.value, "parts": [msg.content]})
            self.chat_session = model.start_chat(history=history)

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        try:
            self._ensure_chat_session()
            response = self.chat_session.send_message(user_message)
            assistant_message = response.text
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except Exception as e:
            raise ValueError(f"Error in Gemini API call: {str(e)}")

    async def cleanup(self):
        self.chat_session = None