from typing import Dict, Optional, List, AsyncGenerator
from ollama import AsyncClient, ChatResponse, ResponseError
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
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

    def __init__(self, model: LLMModel = None, system_message: str = None, custom_config: LLMConfig = None):
        self.ollama_host = os.getenv('OLLAMA_HOST', self.DEFAULT_OLLAMA_HOST)
        logging.info(f"Initializing Ollama with host: {self.ollama_host}")
        
        self.client = AsyncClient(host=self.ollama_host)
        super().__init__(model=model or LLMModel.OLLAMA_LLAMA_3_2, system_message=system_message, custom_config=custom_config)
        logger.info(f"OllamaLLM initialized with model: {self.model}")

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        try:
            response: ChatResponse = await self.client.chat(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages]
            )
            assistant_message = response['message']['content']
            
            # Detect and process reasoning content using <think> markers
            reasoning_content = ""
            main_content = assistant_message
            if "<think>" in assistant_message and "</think>" in assistant_message:
                start_index = assistant_message.index("<think>")
                end_index = assistant_message.index("</think>") + len("</think>")
                # Extract reasoning content and replace markers with standardized tags
                reasoning_segment = assistant_message[start_index:end_index]
                reasoning_content = reasoning_segment.replace("<think>", "<llm_reasoning_token>").replace("</think>", "</llm_reasoning_token>\n")
                # Remove the reasoning segment from the main content
                main_content = assistant_message[:start_index] + assistant_message[end_index:]
                display_content = f"{reasoning_content}\n{main_content}"
            else:
                display_content = assistant_message

            self.add_assistant_message(main_content, reasoning_content=reasoning_content if reasoning_content else None)
            
            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
            
            return CompleteResponse(
                content=display_content,
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
        accumulated_main = ""
        accumulated_reasoning = ""
        in_reasoning = False
        try:
            async for part in await self.client.chat(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages],
                stream=True
            ):
                token = part['message']['content']
                token_stripped = token.strip()
                
                if token_stripped == "<think>":
                    # Yield the standardized reasoning start marker immediately.
                    yield ChunkResponse(content="<llm_reasoning_token>", is_complete=False)
                    in_reasoning = True
                    continue
                elif token_stripped == "</think>":
                    if in_reasoning:
                        # Yield the standardized reasoning closing marker.
                        yield ChunkResponse(content="</llm_reasoning_token>", is_complete=False)
                    in_reasoning = False
                    continue
                else:
                    if in_reasoning:
                        yield ChunkResponse(content=token, is_complete=False)
                        accumulated_reasoning += token
                    else:
                        yield ChunkResponse(content=token, is_complete=False)
                        accumulated_main += token
            
            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
            yield ChunkResponse(content="", is_complete=True, usage=token_usage)
            
            if accumulated_reasoning:
                self.add_assistant_message(accumulated_main, reasoning_content=accumulated_reasoning)
            else:
                self.add_assistant_message(accumulated_main)
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
        await super().cleanup()
