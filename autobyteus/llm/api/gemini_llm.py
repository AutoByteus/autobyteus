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
from autobyteus.llm.user_message import LLMUserMessage

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
        
        if model is None:
            model = LLMModel['gemini-2.5-flash']
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        self.client = self.initialize()
        self.chat_session = None

    @classmethod
    def initialize(cls):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set.")
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
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
                generation_config=self.generation_config,
                system_instruction=self.system_message if self.system_message else None
            )
            history = []
            for msg in self.messages:
                # NOTE: This history conversion will need to be updated for multimodal
                if msg.role == MessageRole.USER or msg.role == MessageRole.ASSISTANT:
                    role = 'model' if msg.role == MessageRole.ASSISTANT else 'user'
                    history.append({"role": role, "parts": [msg.content]})
            # Gemini's chat history does not include system messages.
            # It's set on the model directly.
            self.chat_session = model.start_chat(history=history)

    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        
        # NOTE: This implementation does not yet support multimodal inputs for Gemini.
        # It will only send the text content.

        try:
            self._ensure_chat_session()
            response = await self.chat_session.send_message_async(user_message.content)
            assistant_message = response.text
            self.add_assistant_message(assistant_message)
            
            # The Gemini API via google-generativeai library does not seem to expose
            # token usage stats directly in the response object for simple chat.
            # We will rely on our TokenUsageTrackingExtension for estimation.
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
        
        # NOTE: This implementation does not yet support multimodal inputs for Gemini.
        # It will only send the text content.

        try:
            self._ensure_chat_session()
            response_stream = await self.chat_session.send_message_async(
                user_message.content,
                stream=True
            )

            async for chunk in response_stream:
                chunk_text = chunk.text
                complete_response += chunk_text
                yield ChunkResponse(
                    content=chunk_text,
                    is_complete=False
                )

            self.add_assistant_message(complete_response)

            # NOTE: The Gemini API does not provide token usage for streaming calls.
            # We will rely on our TokenUsageTrackingExtension for estimation.
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
        self.chat_session = None
        await super().cleanup()
