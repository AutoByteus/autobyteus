from typing import List, AsyncGenerator
from ollama import AsyncClient, ChatResponse, ResponseError
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.prompt_renderers.ollama_prompt_renderer import OllamaPromptRenderer
import logging
import httpx

logger = logging.getLogger(__name__)

class OllamaLLM(BaseLLM):
    def __init__(self, model: LLMModel, llm_config: LLMConfig):
        if not model.host_url:
            raise ValueError("OllamaLLM requires a host_url to be set in its LLMModel object.")
            
        logger.info(f"Initializing OllamaLLM for model '{model.name}' with host: {model.host_url}")
        
        self.client = AsyncClient(host=model.host_url)
        
        super().__init__(model=model, llm_config=llm_config)
        self._renderer = OllamaPromptRenderer()
        logger.info(f"OllamaLLM initialized with model: {self.model.model_identifier}")

    async def _send_messages_to_llm(self, messages: List[Message], **kwargs) -> CompleteResponse:
        try:
            formatted_messages = await self._renderer.render(messages)
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

    async def _stream_messages_to_llm(
        self, messages: List[Message], **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        accumulated_main = ""
        accumulated_reasoning = ""
        in_reasoning = False
        final_response = None
        
        try:
            formatted_messages = await self._renderer.render(messages)
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
