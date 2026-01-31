import logging
import inspect
import os
from abc import ABC
from typing import Optional, List, AsyncGenerator, Dict, Any
from openai import OpenAI
from openai.types.completion_usage import CompletionUsage
from openai.types.chat import ChatCompletionChunk

from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.utils.messages import Message
from autobyteus.llm.prompt_renderers.openai_chat_renderer import OpenAIChatRenderer

logger = logging.getLogger(__name__)

class OpenAICompatibleLLM(BaseLLM, ABC):
    def __init__(
        self,
        model: LLMModel,
        api_key_env_var: str,
        base_url: str,
        llm_config: Optional[LLMConfig] = None,
        api_key_default: Optional[str] = None
    ):
        model_default_config = model.default_config if hasattr(model, "default_config") else None
        if model_default_config:
            effective_config = LLMConfig.from_dict(model_default_config.to_dict())
            if llm_config:
                effective_config.merge_with(llm_config)
        else:
            effective_config = llm_config or LLMConfig()

        # Try to get from env
        api_key = os.getenv(api_key_env_var)
        
        # If not in env, try default (explicit check)
        if (api_key is None or api_key == "") and api_key_default is not None:
            api_key = api_key_default
            logger.info(f"{api_key_env_var} not set, using default key: {api_key_default}")

        # Final check
        if not api_key:
             logger.error(f"{api_key_env_var} environment variable is not set and no default provided.")
             raise ValueError(f"{api_key_env_var} environment variable is not set. Default was: {api_key_default}")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Initialized OpenAI compatible client with base_url: {base_url}")
        
        super().__init__(model=model, llm_config=effective_config)
        # Respect user/configured limit; let provider default if unspecified.
        self.max_tokens = effective_config.max_tokens
        self._renderer = OpenAIChatRenderer()

    def _create_token_usage(self, usage_data: Optional[CompletionUsage]) -> Optional[TokenUsage]:
        if not usage_data:
            return None
        return TokenUsage(
            prompt_tokens=usage_data.prompt_tokens,
            completion_tokens=usage_data.completion_tokens,
            total_tokens=usage_data.total_tokens
        )

    async def _send_messages_to_llm(
        self, messages: List[Message], **kwargs
    ) -> CompleteResponse:
        try:
            formatted_messages = await self._renderer.render(messages)
            logger.info("Sending request to %s API", self.model.provider.value)

            params: Dict[str, Any] = {
                "model": self.model.value,
                "messages": formatted_messages,
            }

            if self.max_tokens is not None:
                # For OpenAI-compatible APIs, prefer max_completion_tokens; legacy max_tokens removed.
                params["max_completion_tokens"] = self.max_tokens
            if self.config.extra_params:
                self._apply_extra_params(params, self.config.extra_params)

            if kwargs.get("tools"):
                params["tools"] = kwargs["tools"]
            if kwargs.get("tool_choice") is not None:
                params["tool_choice"] = kwargs["tool_choice"]

            response = self.client.chat.completions.create(**params)
            full_message = response.choices[0].message

            reasoning = None
            if hasattr(full_message, "reasoning_content") and full_message.reasoning_content:
                reasoning = full_message.reasoning_content
            elif "reasoning_content" in full_message and full_message["reasoning_content"]:
                reasoning = full_message["reasoning_content"]

            main_content = ""
            if hasattr(full_message, "content") and full_message.content:
                main_content = full_message.content
            elif "content" in full_message and full_message["content"]:
                main_content = full_message["content"]

            token_usage = self._create_token_usage(response.usage)
            logger.info("Received response from %s API with usage data", self.model.provider.value)

            return CompleteResponse(
                content=main_content,
                reasoning=reasoning,
                usage=token_usage,
            )
        except Exception as e:
            logger.error("Error in %s API request: %s", self.model.provider.value, str(e))
            raise ValueError(f"Error in {self.model.provider.value} API request: {str(e)}")

    async def _stream_messages_to_llm(
        self, messages: List[Message], **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        accumulated_reasoning = ""
        accumulated_content = ""
        tool_calls_logged = False

        try:
            formatted_messages = await self._renderer.render(messages)
            logger.info("Starting streaming request to %s API", self.model.provider.value)

            params: Dict[str, Any] = {
                "model": self.model.value,
                "messages": formatted_messages,
                "stream": True,
                "stream_options": {"include_usage": True},
            }

            if self.max_tokens is not None:
                params["max_completion_tokens"] = self.max_tokens
            if self.config.extra_params:
                self._apply_extra_params(params, self.config.extra_params)

            if kwargs.get("tools"):
                params["tools"] = kwargs["tools"]
            if kwargs.get("tool_choice") is not None:
                params["tool_choice"] = kwargs["tool_choice"]

            stream = self.client.chat.completions.create(**params)

            for chunk in stream:
                chunk: ChatCompletionChunk
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                reasoning_chunk = None
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning_chunk = delta.reasoning_content
                elif isinstance(delta, dict) and "reasoning_content" in delta and delta["reasoning_content"]:
                    reasoning_chunk = delta["reasoning_content"]

                if reasoning_chunk:
                    accumulated_reasoning += reasoning_chunk
                    yield ChunkResponse(content="", reasoning=reasoning_chunk)

                tool_call_deltas = None
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    from autobyteus.llm.converters.openai_tool_call_converter import convert_openai_tool_calls
                    tool_call_deltas = convert_openai_tool_calls(delta.tool_calls)
                    if tool_call_deltas and not tool_calls_logged:
                        logger.info(
                            "Streaming tool call deltas received from %s (count=%d).",
                            self.model.provider.value,
                            len(tool_call_deltas),
                        )
                        tool_calls_logged = True

                main_token = delta.content

                if main_token or tool_call_deltas:
                    if main_token:
                        accumulated_content += main_token
                    yield ChunkResponse(
                        content=main_token or "",
                        reasoning=None,
                        tool_calls=tool_call_deltas,
                    )

                if hasattr(chunk, "usage") and chunk.usage is not None:
                    token_usage = self._create_token_usage(chunk.usage)
                    yield ChunkResponse(
                        content="",
                        reasoning=None,
                        is_complete=True,
                        usage=token_usage,
                    )

            logger.info("Completed streaming response from %s API", self.model.provider.value)

        except Exception as e:
            logger.error("Error in %s API streaming: %s", self.model.provider.value, str(e))
            raise ValueError(f"Error in {self.model.provider.value} API streaming: {str(e)}")

    def _apply_extra_params(self, params: Dict[str, Any], extra_params: Dict[str, Any]) -> None:
        # Use extra_body for provider-specific fields not in the OpenAI client signature.
        if not extra_params:
            return
        extra = dict(extra_params)
        allowed = self._get_chat_completion_param_names()

        if any(key not in allowed for key in extra.keys()):
            existing_body = params.get("extra_body")
            if isinstance(existing_body, dict):
                merged = dict(existing_body)
                merged.update(extra)
                params["extra_body"] = merged
            else:
                params["extra_body"] = extra
        else:
            params.update(extra)

    def _get_chat_completion_param_names(self) -> set:
        try:
            return self._chat_completion_param_names
        except AttributeError:
            allowed = set(inspect.signature(self.client.chat.completions.create).parameters.keys())
            self._chat_completion_param_names = allowed
            return allowed


class OpenAIChatCompletionsLLM(OpenAICompatibleLLM):
    """Strict OpenAI Chat Completions client: rejects unsupported extra params."""

    def _apply_extra_params(self, params: Dict[str, Any], extra_params: Dict[str, Any]) -> None:
        if not extra_params:
            return
        extra = dict(extra_params)
        allowed = self._get_chat_completion_param_names()
        unknown = [key for key in extra.keys() if key not in allowed]
        if unknown:
            raise ValueError(
                "Unsupported OpenAI chat.completions params: "
                + ", ".join(sorted(unknown))
            )
        params.update(extra)

    async def cleanup(self):
        await super().cleanup()
