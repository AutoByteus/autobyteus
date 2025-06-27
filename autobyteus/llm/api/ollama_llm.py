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

    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        self.ollama_host = os.getenv('DEFAULT_OLLAMA_HOST', self.DEFAULT_OLLAMA_HOST)
        logger.info(f"Initializing Ollama with host: {self.ollama_host}")
        
        self.client = AsyncClient(host=self.ollama_host)
        
        # Provide defaults if not specified
        if model is None:
            model = LLMModel.OLLAMA_LLAMA_3_2
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        logger.info(f"OllamaLLM initialized with model: {self.model}")

    async def _send_user_message_to_llm(self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        try:
            response: ChatResponse = await self.client.chat(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages]
            )
            assistant_message = response['message']['content']
            
            # Detect and process reasoning content using <think> markers
            reasoning_content = None
            main_content = assistant_message
            if "<think>" in assistant_message and "</think>" in assistant_message:
                start_index = assistant_message.find("<think>")
                end_index = assistant_message.find("</think>")
                if start_index < end_index:
                    reasoning_content = assistant_message[start_index + len("<think>"):end_index].strip()
                    main_content = (assistant_message[:start_index] + assistant_message[end_index + len("</think>"):])
            
            self.add_assistant_message(main_content, reasoning_content=reasoning_content)
            
            token_usage = TokenUsage(
                prompt_tokens=response.get('prompt_eval_count', 0),
                completion_tokens=response.get('eval_count', 0),
                total_tokens=response.get('prompt_eval_count', 0) + response.get('eval_count', 0)
            )
            
            return CompleteResponse(
                content=main_content.strip(),
                reasoning=reasoning_content,
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
        self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        accumulated_main = ""
        accumulated_reasoning = ""
        in_reasoning = False
        final_response = None
        
        try:
            async for part in await self.client.chat(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages],
                stream=True
            ):
                token = part['message']['content']
                
                # Simple state machine for <think> tags
                if "<think>" in token:
                    in_reasoning = True
                    # In case token is like "...</think><think>...", handle it
                    parts = token.split("<think>")
                    token = parts[-1]

                if "</think>" in token:
                    in_reasoning = False
                    parts = token.split("</think>")
                    token = parts[-1]

                if in_reasoning:
                    accumulated_reasoning += token
                    yield ChunkResponse(content="", reasoning=token)
                else:
                    accumulated_main += token
                    yield ChunkResponse(content=token, reasoning=None)

                if part.get('done'):
                    final_response = part
            
            token_usage = None
            if final_response:
                token_usage = TokenUsage(
                    prompt_tokens=final_response.get('prompt_eval_count', 0),
                    completion_tokens=final_response.get('eval_count', 0),
                    total_tokens=final_response.get('prompt_eval_count', 0) + final_response.get('eval_count', 0)
                )

            yield ChunkResponse(content="", reasoning=None, is_complete=True, usage=token_usage)
            
            self.add_assistant_message(accumulated_main, reasoning_content=accumulated_reasoning)

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