
import logging
from typing import Dict, Optional, List, AsyncGenerator
import google.generativeai as genai
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

logger = logging.getLogger(__name__)

class GeminiLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, system_message: str = None, custom_config: LLMConfig = None):
        self.generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        super().__init__(model=model or LLMModel.GEMINI_1_5_FLASH_API, system_message=system_message, custom_config=custom_config)
        self.client = self.initialize()
        self.chat_session = None

    @classmethod
    def initialize(cls):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set.")
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            genai.configure(api_key=api_key)
            return genai
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")

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

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        try:
            self._ensure_chat_session()
            response = self.chat_session.send_message(user_message)
            assistant_message = response.text
            self.add_assistant_message(assistant_message)
            
            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
            
            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Gemini API call: {str(e)}")
            raise ValueError(f"Error in Gemini API call: {str(e)}")
    
    async def cleanup(self):
        self.chat_session = None
        super().cleanup()
