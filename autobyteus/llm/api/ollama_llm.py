from typing import Dict, Optional, List, AsyncGenerator, Any
from ollama import AsyncClient, ChatResponse, ResponseError
from ollama import Image  # FIX: Import the Image type from the ollama library
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.media_payload_formatter import image_source_to_base64
import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)

class OllamaLLM(BaseLLM):
    def __init__(self, model: LLMModel, llm_config: LLMConfig):
        if not model.host_url:
            raise ValueError("OllamaLLM requires a host_url to be set in its LLMModel object.")
            
        logger.info(f"Initializing OllamaLLM for model '{model.name}' with host: {model.host_url}")
        
        self.client = AsyncClient(host=model.host_url)
        
        super().__init__(model=model, llm_config=llm_config)
        logger.info(f"OllamaLLM initialized with model: {self.model.model_identifier}")

    async def _format_ollama_messages(self) -> List[Dict[str, Any]]:
        """
        Formats the conversation history for the Ollama API, including multimodal content.
        """
        formatted_messages = []
        for msg in self.messages:
            msg_dict = {
                "role": msg.role.value,
                "content": msg.content or ""
            }
            if msg.image_urls:
                try:
                    # Concurrently process all images using the centralized utility
                    image_tasks = [image_source_to_base64(url) for url in msg.image_urls]
                    prepared_base64_images = await asyncio.gather(*image_tasks)
                    if prepared_base64_images:
                        # FIX: Wrap each base64 string in the official ollama.Image object
                        msg_dict["images"] = [Image(value=b64_string) for b64_string in prepared_base64_images]
                except Exception as e:
                    logger.error(f"Error processing images for Ollama, skipping them. Error: {e}")

            formatted_messages.append(msg_dict)
        return formatted_messages

    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)

        try:
            formatted_messages = await self._format_ollama_messages()
            response: ChatResponse = await self.client.chat(
                model=self.model.value,
                messages=formatted_messages
            )
            assistant_message = response['message']['content']
            
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
        self, user_message: LLMUserMessage, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        accumulated_main = ""
        accumulated_reasoning = ""
        in_reasoning = False
        final_response = None
        
        try:
            formatted_messages = await self._format_ollama_messages()
            async for part in await self.client.chat(
                model=self.model.value,
                messages=formatted_messages,
                stream=True
            ):
                token = part['message']['content']
                
                if "<think>" in token:
                    in_reasoning = True
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
