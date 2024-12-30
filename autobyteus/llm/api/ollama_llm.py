from typing import Dict, Optional, List, AsyncGenerator
from ollama import AsyncClient, ChatResponse, ResponseError
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message
import logging
import asyncio
import httpx
import os

class OllamaLLM(BaseLLM):
    DEFAULT_OLLAMA_HOST = 'http://localhost:11434'

    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.ollama_host = os.getenv('OLLAMA_HOST', self.DEFAULT_OLLAMA_HOST)
        logging.info(f"Initializing Ollama with host: {self.ollama_host}")
        
        self.client = AsyncClient(host=self.ollama_host)
        self.model = model_name.value if model_name else "llama3.2"
        self.system_message = system_message or "You are a helpful assistant."
        self.messages = []
        super().__init__(model=self.model)

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        retries = 3
        for attempt in range(retries):
            try:
                response: ChatResponse = await self.client.chat(
                    model=self.model,
                    messages=[msg.to_dict() for msg in self.messages]
                )
                assistant_message = response.message.content
                self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
                return assistant_message
            except httpx.HTTPError as e:
                logging.error(f"HTTP Error in Ollama call (attempt {attempt + 1}/{retries}): {e.response.status_code} - {e.response.text}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise  # Re-raise the HTTPError for higher-level handling
            except ResponseError as e:
                logging.error(f"Ollama Response Error (attempt {attempt + 1}/{retries}): {e.error} - Status Code: {e.status_code}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
            except Exception as e:
                logging.exception(f"Unexpected error in Ollama call (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        self.messages.append(Message(MessageRole.USER, user_message))
        complete_response = ""
        retries = 3
        for attempt in range(retries):
            try:
                async for part in await self.client.chat(
                    model=self.model,
                    messages=[msg.to_dict() for msg in self.messages],
                    stream=True
                ):
                    complete_response += part['message']['content']
                    yield part['message']['content']

                self.messages.append(Message(MessageRole.ASSISTANT, complete_response))
                break
            except httpx.HTTPError as e:
                logging.error(f"HTTP Error in Ollama streaming (attempt {attempt + 1}/{retries}): {e.response.status_code} - {e.response.text}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
            except ResponseError as e:
                logging.error(f"Ollama Response Error in streaming (attempt {attempt + 1}/{retries}): {e.error} - Status Code: {e.status_code}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
            except Exception as e:
                logging.exception(f"Unexpected error in Ollama streaming (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

    async def cleanup(self):
        pass # No cleanup needed for Ollama
