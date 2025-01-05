
from typing import Dict, Optional, List, AsyncGenerator
from ollama import AsyncClient, ChatResponse, ResponseError
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
import logging
import asyncio
import httpx
import os

logger = logging.getLogger(__name__)

class OllamaLLM(BaseLLM):
    DEFAULT_OLLAMA_HOST = 'http://localhost:11434'

    def __init__(self, model: LLMModel = None, system_message: str = None):
        self.ollama_host = os.getenv('OLLAMA_HOST', self.DEFAULT_OLLAMA_HOST)
        logging.info(f"Initializing Ollama with host: {self.ollama_host}")
        
        self.client = AsyncClient(host=self.ollama_host)
        super().__init__(model=model or LLMModel.OLLAMA_LLAMA_3_2, system_message=system_message)
        logger.info(f"OllamaLLM initialized with model: {self.model}")

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        try:
            response: ChatResponse = await self.client.chat(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages]
            )
            assistant_message = response['message']['content']
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
        except httpx.HTTPError as e:
            logging.error(f"HTTP Error in Ollama call: {e.response.status_code} - {e.response.text}")
            raise
        except ResponseError as e:
            logging.error(f"Ollama Response Error: {e.error} - Status Code: {e.status_code}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in Ollama call: {e}")
            raise

    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        complete_response = ""
        try:
            async for part in await self.client.chat(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages],
                stream=True
            ):
                complete_response += part['message']['content']
                yield ChunkResponse(
                    content=part['message']['content'],
                    is_complete=False
                )
            
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

            self.add_assistant_message(complete_response)
        except httpx.HTTPError as e:
            logging.error(f"HTTP Error in Ollama streaming: {e.response.status_code} - {e.response.text}")
            raise
        except ResponseError as e:
            logging.error(f"Ollama Response Error in streaming: {e.error} - Status Code: {e.status_code}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in Ollama streaming: {e}")
            raise

    async def cleanup(self):
        super().cleanup()
