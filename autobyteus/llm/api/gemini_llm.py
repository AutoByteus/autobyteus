import logging
from typing import Dict, Optional, List, AsyncGenerator
import google.generativeai as genai
from google.generativeai import types
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

logger = logging.getLogger(__name__)

class GeminiLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        self.generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        
        # Provide defaults if not specified
        model = model or LLMModel.GEMINI_2_0_FLASH_API
        llm_config = llm_config or LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        self.initialize()
        self.model_instance = genai.GenerativeModel(
            model_name=self.model.value,
            generation_config=self.generation_config,
            system_instruction=self.system_message
        )

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
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")

    def _prepare_history(self) -> List[Dict]:
        history = []
        for msg in self.messages:
            if msg.role == MessageRole.SYSTEM:
                continue
            role = 'model' if msg.role == MessageRole.ASSISTANT else msg.role.value
            if isinstance(msg.content, str):
                history.append({"role": role, "parts": [msg.content]})
            else:
                history.append({"role": role, "parts": msg.content})
        return history

    async def _send_user_message_to_llm(self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        try:
            history = self._prepare_history()
            response = await self.model_instance.generate_content_async(history)
            assistant_message = response.text
            self.add_assistant_message(assistant_message)
            
            token_usage = None
            if hasattr(response, 'usage_metadata'):
                usage_meta = response.usage_metadata
                token_usage = TokenUsage(
                    prompt_tokens=usage_meta.prompt_token_count,
                    completion_tokens=usage_meta.candidates_token_count,
                    total_tokens=usage_meta.total_token_count
                )
            
            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Gemini API call: {str(e)}")
            raise ValueError(f"Error in Gemini API call: {str(e)}")
    
    async def _stream_user_message_to_llm(self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        history = self._prepare_history()
        try:
            stream = await self.model_instance.generate_content_async(history, stream=True)
            
            accumulated_content = ""
            final_response = None
            async for chunk in stream:
                if hasattr(chunk, 'text') and chunk.text:
                    accumulated_content += chunk.text
                    yield ChunkResponse(content=chunk.text, is_complete=False, usage=None)
                final_response = chunk
            
            self.add_assistant_message(accumulated_content)
            
            usage = None
            if final_response and hasattr(final_response, 'usage_metadata'):
                usage_meta = final_response.usage_metadata
                usage = TokenUsage(
                    prompt_tokens=usage_meta.prompt_token_count,
                    completion_tokens=usage_meta.candidates_token_count,
                    total_tokens=usage_meta.total_token_count
                )
            
            yield ChunkResponse(content="", is_complete=True, usage=usage)

        except Exception as e:
            logger.error(f"Error in Gemini API streaming call: {str(e)}")
            raise ValueError(f"Error in Gemini API streaming call: {str(e)}")

    async def cleanup(self):
        super().cleanup()
