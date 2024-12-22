from typing import Dict, Optional, List, AsyncGenerator
import google.generativeai as genai
import os
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
                model_name=self.model, generation_config=self.generation_config
            )

            history = []
            for msg in self.messages:
                history.append({"role": msg.role.value, "parts": [msg.content]})
            self.chat_session = model.start_chat(history=history)

    async def _send_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        try:
            ## Not required
            # self._ensure_chat_session()

            ## Updating with new api docs
            # https://ai.google.dev/gemini-api/docs/text-generation?lang=python
            model = self.client.GenerativeModel(
                model_name=self.model, generation_config=self.generation_config
            )

            response = model.generate_content(user_message)

            assistant_message = response.text

            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except Exception as e:
            raise ValueError(f"Error in Gemini API call: {str(e)}")

    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream responses from Mistral API token by token using async streaming.
        """
        self.messages.append(Message(MessageRole.USER, user_message))
        accumulated_message = ""

        try:
            model = self.client.GenerativeModel(
                model_name=self.model, generation_config=self.generation_config
            )

            response = model.generate_content(user_message, stream=True)
            for chunk in response:
                accumulated_message += chunk.text
                yield chunk.text

            # After streaming is complete, store the full message
            self.messages.append(Message(MessageRole.ASSISTANT, accumulated_message))

        except Exception as e:
            raise ValueError(f"Error in Gemini streaming call: {str(e)}")

    async def cleanup(self):
        self.chat_session = None
