from typing import List, Any, AsyncGenerator
import os
import logging
import httpx
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from mistralai import Mistral
from autobyteus.llm.utils.messages import Message
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.prompt_renderers.mistral_prompt_renderer import MistralPromptRenderer

logger = logging.getLogger(__name__)

class MistralLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        if model is None:
            model = LLMModel['mistral-large']
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        # Let the SDK manage its own HTTP client. Passing a raw httpx client
        # does not satisfy the SDK's HttpClient protocol and raises an
        # AssertionError during construction (observed in tests). Rely on the
        # internal client instead.
        self.client: Mistral = self._initialize()
        self._renderer = MistralPromptRenderer()
        logger.info(f"MistralLLM initialized with model: {self.model}")

    def _initialize(self) -> Mistral:
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_api_key:
            logger.error("MISTRAL_API_KEY environment variable is not set")
            raise ValueError("MISTRAL_API_KEY environment variable is not set.")
        try:
            return Mistral(api_key=mistral_api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Mistral client: {str(e)}")
            raise ValueError(f"Failed to initialize Mistral client: {str(e)}")

    def _create_token_usage(self, usage_data: Any) -> TokenUsage:
        """Convert Mistral usage data to TokenUsage format."""
        return TokenUsage(
            prompt_tokens=usage_data.prompt_tokens,
            completion_tokens=usage_data.completion_tokens,
            total_tokens=usage_data.total_tokens
        )

    async def _send_messages_to_llm(
        self, messages: List[Message], **kwargs
    ) -> CompleteResponse:
        try:
            mistral_messages = await self._renderer.render(messages)
            
            chat_response = await self.client.chat.complete_async(
                model=self.model.value,
                messages=mistral_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )

            assistant_message = chat_response.choices[0].message.content

            token_usage = self._create_token_usage(chat_response.usage)
            logger.debug(f"Token usage recorded: {token_usage}")

            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Mistral API call: {str(e)}")
            raise ValueError(f"Error in Mistral API call: {str(e)}")
    
    async def _stream_messages_to_llm(
        self, messages: List[Message], **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        accumulated_message = ""
        final_usage = None
        
        try:
            mistral_messages = await self._renderer.render(messages)
            
            # Raw HTTP streaming to bypass SDK validation issues with tool calls
            api_key = os.environ.get("MISTRAL_API_KEY")
            if not api_key:
                raise ValueError("MISTRAL_API_KEY not set")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
            
            payload = {
                "model": self.model.value,
                "messages": mistral_messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "top_p": self.config.top_p,
                "stream": True
            }
            # Filter None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            if kwargs.get("tools"):
                payload["tools"] = kwargs.get("tools")
                payload["tool_choice"] = "auto"

            # Use internal httpx client logic or create new one context
            async with httpx.AsyncClient() as client:
                req = client.build_request("POST", "https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=60.0)
                # Do not set stream=True for python client, let it buffer content automatically.
                # The API will still stream SSE but client reads until close.
                response = await client.send(req)
                
                try:
                    if response.status_code != 200:
                        # response.read() is not needed if stream=False, it's already read
                        error_text = response.text
                        raise ValueError(f"Mistral API error: {response.status_code} - {error_text}")

                    buffer = ""
                    # Content is already in response.text
                    buffer = response.text
                    
                    # Split buffer into lines and process like stream
                    lines = buffer.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line or line == "":
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            
                            try:
                                import json
                                chunk_data = json.loads(data_str)
                                
                                if "choices" in chunk_data and chunk_data["choices"]:
                                    choice = chunk_data["choices"][0]
                                    delta = choice.get("delta", {})
                                    
                                    if "tool_calls" in delta and delta["tool_calls"]:
                                        from autobyteus.llm.converters.mistral_tool_call_converter import convert_mistral_tool_calls
                                        tool_calls = convert_mistral_tool_calls(delta["tool_calls"])
                                        if tool_calls:
                                            yield ChunkResponse(
                                                content="",
                                                tool_calls=tool_calls,
                                                is_complete=False
                                            )

                                    content = delta.get("content")
                                    if content:
                                         accumulated_message += content
                                         yield ChunkResponse(content=content, is_complete=False)
                                
                                if chunk_data.get("usage"):
                                     final_usage_data = chunk_data.get("usage")
                                     from collections import namedtuple
                                     UsageObj = namedtuple('UsageObj', ['prompt_tokens', 'completion_tokens', 'total_tokens'])
                                     usage_obj = UsageObj(
                                        prompt_tokens=final_usage_data.get('prompt_tokens', 0),
                                        completion_tokens=final_usage_data.get('completion_tokens', 0),
                                        total_tokens=final_usage_data.get('total_tokens', 0)
                                     )
                                     final_usage = self._create_token_usage(usage_obj)

                            except json.JSONDecodeError:
                                logger.warning(f"Failed to decode Mistral stream line: {line}")
                                continue
                finally:
                    await response.aclose()

            # Yield the final chunk
            yield ChunkResponse(
                content="",
                is_complete=True,
                usage=final_usage
            )
            
        except Exception as e:
            logger.error(f"Error in Mistral API streaming call: {str(e)}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error in Mistral API streaming call: {str(e)}")
    
    async def cleanup(self):
        logger.debug("Cleaning up MistralLLM instance")
        await super().cleanup()
