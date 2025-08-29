import logging
from typing import Dict, List, AsyncGenerator, Any
import google.generativeai as genai  # CHANGED: Using the older 'google.generativeai' library
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
    """
    Formats internal message history for the Gemini API.
    This function remains compatible with the older library.
    """
    history = []
    # System message is handled separately in the model initialization
    for msg in messages:
        if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
            role = 'model' if msg.role == MessageRole.ASSISTANT else 'user'
            history.append({"role": role, "parts": [{"text": msg.content}]})
    return history

class GeminiLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        if model is None:
            model = LLMModel['gemini-2.5-flash'] # Note: Ensure model name is compatible, e.g., 'gemini-1.5-flash-latest'
        if llm_config is None:
            llm_config = LLMConfig()

        super().__init__(model=model, llm_config=llm_config)
        
        # CHANGED: Initialization flow. Configure API key and then instantiate the model.
        self.initialize()
        
        system_instruction = self.system_message if self.system_message else None
        
        self.model = genai.GenerativeModel(
            model_name=self.model.value,
            system_instruction=system_instruction
        )

    @staticmethod
    def initialize():
        """
        CHANGED: This method now configures the genai library with the API key
        instead of creating a client instance.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set.")
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {str(e)}")
            raise ValueError(f"Failed to configure Gemini client: {str(e)}")

    def _get_generation_config(self) -> Dict[str, Any]:
        """
        CHANGED: Builds the generation config as a dictionary.
        'thinking_config' is not available in the old library.
        'system_instruction' is passed during model initialization.
        """
        # Basic configuration, you can expand this with temperature, top_p, etc.
        # from self.llm_config if needed.
        config = {
            "response_mime_type": "text/plain",
            # Example: "temperature": self.llm_config.temperature
        }
        return config

    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        
        try:
            history = _format_gemini_history(self.messages)
            generation_config = self._get_generation_config()

            # CHANGED: API call now uses the model instance directly.
            response = await self.model.generate_content_async(
                contents=history,
                generation_config=generation_config,
            )
            
            assistant_message = response.text
            self.add_assistant_message(assistant_message)
            
            # CHANGED: Token usage is extracted from 'usage_metadata'.
            token_usage = TokenUsage(
                prompt_tokens=response.usage_metadata.prompt_token_count,
                completion_tokens=response.usage_metadata.candidates_token_count,
                total_tokens=response.usage_metadata.total_token_count
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

            # CHANGED: API call for streaming is now part of generate_content_async.
            response_stream = await self.model.generate_content_async(
                contents=history,
                generation_config=generation_config,
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

            # NOTE: The old library's async stream does not easily expose token usage.
            # Keeping it at 0, consistent with your original implementation.
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
