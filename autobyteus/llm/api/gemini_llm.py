
import logging
from typing import Dict, Optional, List
import google.generativeai as genai
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message

logger = logging.getLogger(__name__)

class GeminiLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, system_message: str = None):
        self.generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        super().__init__(model=model or LLMModel.GEMINI_1_5_FLASH_API, system_message=system_message)
        self.client = self.initialize()
        self.chat_session = None
        logger.info(f"GeminiLLM initialized with model: {self.model}")

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
                model_name=self.model.value,
                generation_config=self.generation_config
            )
            history = []
            for msg in self.messages:
                history.append({"role": msg.role.value, "parts": [msg.content]})
            self.chat_session = model.start_chat(history=history)

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.add_user_message(user_message)
        try:
            self._ensure_chat_session()
            response = self.chat_session.send_message(user_message)
            assistant_message = response.text
            self.add_assistant_message(assistant_message)
            return assistant_message
        except Exception as e:
            raise ValueError(f"Error in Gemini API call: {str(e)}")
    
    async def cleanup(self):
        self.chat_session = None
        super().cleanup()
