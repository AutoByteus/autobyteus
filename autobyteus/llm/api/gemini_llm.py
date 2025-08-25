import logging
from typing import Dict, Optional, List, AsyncGenerator, Any
from google import genai
from google.genai import types as genai_types
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.user_message import LLMUserMessage

logger = logging.getLogger(__name__)

def _format_gemini_history(messages: List[Message]) -> List[Dict[str, Any]]:
    """Formats internal message history for the Gemini API."""
    history = []
    # System message is handled separately in the new API
    for msg in messages:
        if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
            # NOTE: This history conversion will need to be updated for multimodal messages
            role = 'model' if msg.role == MessageRole.ASSISTANT else 'user'
            # The `parts` must be a list of dictionaries (Part objects), not a list of strings.
            history.append({"role": role, "parts": [{"text": msg.content}]})
    return history

class GeminiLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        self.generation_config_dict = {
            "response_mime_type": "text/plain",
        }
        
        if model is None:
            model = LLMModel['gemini-2.5-flash']
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        self.client = self.initialize()
        self.async_client = self.client.aio

    @classmethod
    def initialize(cls) -> genai.client.Client:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set.")
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        try:
            return genai.Client()
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")

    def _get_generation_config(self) -> genai_types.GenerateContentConfig:
        """Builds the generation config, handling special cases like 'thinking'."""
        config = self.generation_config_dict.copy()

        thinking_config = None
        if "flash" in self.model.value:
            thinking_config = genai_types.ThinkingConfig(thinking_budget=0)
        
        # System instruction is now part of the config
        system_instruction = self.system_message if self.system_message else None
        
        return genai_types.GenerateContentConfig(
            **config,
            thinking_config=thinking_config,
            system_instruction=system_instruction
        )

    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        
        try:
            history = _format_gemini_history(self.messages)
            generation_config = self._get_generation_config()

            response = await self.async_client.models.generate_content(
                model=f"models/{self.model.value}",
                contents=history,
                config=generation_config,
            )
            
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
    
    async def _stream_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        complete_response = ""
        
        try:
            history = _format_gemini_history(self.messages)
            generation_config = self._get_generation_config()

            response_stream = await self.async_client.models.generate_content_stream(
                model=f"models/{self.model.value}",
                contents=history,
                config=generation_config,
            )

            async for chunk in response_stream:
                chunk_text = chunk.text
                complete_response += chunk_text
                yield ChunkResponse(
                    content=chunk_text,
                    is_complete=False
                )

            self.add_assistant_message(complete_response)

            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )

            yield ChunkResponse(
                content="",
                is_complete=True,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Gemini API streaming call: {str(e)}")
            raise ValueError(f"Error in Gemini API streaming call: {str(e)}")

    async def cleanup(self):
        await super().cleanup()
