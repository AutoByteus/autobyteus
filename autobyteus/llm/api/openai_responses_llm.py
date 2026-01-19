import logging
import os
import asyncio
from typing import Optional, List, AsyncGenerator, Dict, Any

from openai import OpenAI
from openai.types.responses import ResponseStreamEvent

from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import Message
from autobyteus.llm.utils.media_payload_formatter import (
    media_source_to_base64,
    create_data_uri,
    get_mime_type,
    is_valid_media_path,
)
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta

logger = logging.getLogger(__name__)


async def _format_responses_history(messages: List[Message]) -> List[Dict[str, Any]]:
    formatted_messages: List[Dict[str, Any]] = []

    for msg in messages:
        if msg.image_urls or msg.audio_urls or msg.video_urls:
            content_parts: List[Dict[str, Any]] = []
            if msg.content:
                content_parts.append({"type": "input_text", "text": msg.content})

            image_tasks = []
            if msg.image_urls:
                for url in msg.image_urls:
                    image_tasks.append(media_source_to_base64(url))

            try:
                base64_images = await asyncio.gather(*image_tasks)
                for i, b64_image in enumerate(base64_images):
                    original_url = msg.image_urls[i]
                    mime_type = (
                        get_mime_type(original_url)
                        if is_valid_media_path(original_url)
                        else "image/jpeg"
                    )
                    data_uri = create_data_uri(mime_type, b64_image)["image_url"]["url"]
                    content_parts.append(
                        {
                            "type": "input_image",
                            "image_url": data_uri,
                            "detail": "auto",
                        }
                    )
            except Exception as e:
                logger.error(f"Error processing one or more images: {e}")

            if msg.audio_urls:
                logger.warning("OpenAI Responses input does not yet support audio; skipping.")
            if msg.video_urls:
                logger.warning("OpenAI Responses input does not yet support video; skipping.")

            formatted_messages.append(
                {"type": "message", "role": msg.role.value, "content": content_parts}
            )
        else:
            formatted_messages.append(
                {"type": "message", "role": msg.role.value, "content": msg.content or ""}
            )

    return formatted_messages


class OpenAIResponsesLLM(BaseLLM):
    def __init__(
        self,
        model: LLMModel,
        api_key_env_var: str,
        base_url: str,
        llm_config: Optional[LLMConfig] = None,
        api_key_default: Optional[str] = None,
    ):
        model_default_config = model.default_config if hasattr(model, "default_config") else None
        if model_default_config:
            effective_config = LLMConfig.from_dict(model_default_config.to_dict())
            if llm_config:
                effective_config.merge_with(llm_config)
        else:
            effective_config = llm_config or LLMConfig()

        api_key = os.getenv(api_key_env_var)
        if not api_key:
            api_key = api_key_default

        if not api_key:
            raise ValueError(f"Missing API key. Set env var {api_key_env_var} or provide api_key_default.")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Initialized OpenAI Responses client with base_url: {base_url}")

        super().__init__(model=model, llm_config=effective_config)
        self.max_tokens = effective_config.max_tokens

    def _create_token_usage(self, usage_data) -> Optional[TokenUsage]:
        if not usage_data:
            return None
        return TokenUsage(
            prompt_tokens=usage_data.input_tokens,
            completion_tokens=usage_data.output_tokens,
            total_tokens=usage_data.total_tokens,
        )

    @staticmethod
    def _extract_output_content(output_items: List[Any]) -> (str, Optional[str]):
        content_chunks: List[str] = []
        reasoning_chunks: List[str] = []

        for item in output_items:
            item_type = getattr(item, "type", None)
            if item_type == "message":
                for content_part in getattr(item, "content", []) or []:
                    if getattr(content_part, "type", None) == "output_text":
                        content_chunks.append(content_part.text)
            elif item_type == "reasoning":
                for summary in getattr(item, "summary", []) or []:
                    if getattr(summary, "type", None) == "summary_text":
                        reasoning_chunks.append(summary.text)

        content = "".join(content_chunks)
        reasoning = "".join(reasoning_chunks) if reasoning_chunks else None
        return content, reasoning

    def _build_reasoning_param(self) -> Optional[Dict[str, Any]]:
        if not self.config.extra_params:
            return None

        reasoning_effort = self.config.extra_params.get("reasoning_effort")
        reasoning_summary = self.config.extra_params.get("reasoning_summary")

        reasoning: Dict[str, Any] = {}
        if reasoning_effort:
            reasoning["effort"] = reasoning_effort
        if reasoning_summary and reasoning_summary != "none":
            reasoning["summary"] = reasoning_summary

        return reasoning or None

    def _filter_extra_params(self) -> Dict[str, Any]:
        if not self.config.extra_params:
            return {}
        filtered = dict(self.config.extra_params)
        filtered.pop("reasoning_effort", None)
        filtered.pop("reasoning_summary", None)
        return filtered

    @staticmethod
    def _normalize_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for tool in tools:
            if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
                fn = tool["function"]
                normalized.append({
                    "type": "function",
                    "name": fn.get("name"),
                    "description": fn.get("description"),
                    "parameters": fn.get("parameters"),
                })
            else:
                normalized.append(tool)
        return normalized

    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)

        try:
            formatted_messages = await _format_responses_history(self.messages)
            logger.info(f"Sending request to {self.model.provider.value} Responses API")

            params: Dict[str, Any] = {
                "model": self.model.value,
                "input": formatted_messages,
            }

            if self.max_tokens is not None:
                params["max_output_tokens"] = self.max_tokens

            reasoning_param = self._build_reasoning_param()
            if reasoning_param:
                params["reasoning"] = reasoning_param

            extra_params = self._filter_extra_params()
            if extra_params:
                params.update(extra_params)

            if kwargs.get("tools"):
                params["tools"] = self._normalize_tools(kwargs["tools"])
            if kwargs.get("tool_choice") is not None:
                params["tool_choice"] = kwargs["tool_choice"]

            response = self.client.responses.create(**params)

            content, reasoning = self._extract_output_content(response.output)
            self.add_assistant_message(content, reasoning_content=reasoning)

            token_usage = self._create_token_usage(response.usage)
            logger.info(f"Received response from {self.model.provider.value} Responses API")

            return CompleteResponse(content=content, reasoning=reasoning, usage=token_usage)
        except Exception as e:
            logger.error(f"Error in {self.model.provider.value} Responses API request: {str(e)}")
            raise ValueError(f"Error in {self.model.provider.value} Responses API request: {str(e)}")

    async def _stream_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)

        accumulated_content = ""
        accumulated_reasoning = ""
        tool_call_state: Dict[int, Dict[str, Any]] = {}
        text_delta_seen: set[str] = set()
        summary_delta_seen: set[str] = set()

        try:
            formatted_messages = await _format_responses_history(self.messages)
            logger.info(f"Starting streaming request to {self.model.provider.value} Responses API")

            params: Dict[str, Any] = {
                "model": self.model.value,
                "input": formatted_messages,
                "stream": True,
            }

            if self.max_tokens is not None:
                params["max_output_tokens"] = self.max_tokens

            reasoning_param = self._build_reasoning_param()
            if reasoning_param:
                params["reasoning"] = reasoning_param

            extra_params = self._filter_extra_params()
            if extra_params:
                params.update(extra_params)

            if kwargs.get("tools"):
                params["tools"] = self._normalize_tools(kwargs["tools"])
            if kwargs.get("tool_choice") is not None:
                params["tool_choice"] = kwargs["tool_choice"]

            stream = self.client.responses.create(**params)

            for event in stream:
                event: ResponseStreamEvent
                event_type = getattr(event, "type", None)

                if event_type == "response.output_text.delta":
                    text_delta_seen.add(event.item_id)
                    accumulated_content += event.delta
                    yield ChunkResponse(content=event.delta, reasoning=None)
                    continue

                if event_type == "response.output_text.done":
                    if event.item_id not in text_delta_seen:
                        accumulated_content += event.text
                        yield ChunkResponse(content=event.text, reasoning=None)
                    continue

                if event_type == "response.reasoning_summary_text.delta":
                    summary_delta_seen.add(event.item_id)
                    accumulated_reasoning += event.delta
                    yield ChunkResponse(content="", reasoning=event.delta)
                    continue

                if event_type == "response.reasoning_summary_text.done":
                    if event.item_id not in summary_delta_seen:
                        accumulated_reasoning += event.text
                        yield ChunkResponse(content="", reasoning=event.text)
                    continue

                if event_type == "response.output_item_added":
                    item = event.item
                    if getattr(item, "type", None) == "function_call":
                        tool_call_state[event.output_index] = {
                            "call_id": item.call_id,
                            "name": item.name,
                            "args_seen": False,
                            "emitted": True,
                        }
                        yield ChunkResponse(
                            content="",
                            reasoning=None,
                            tool_calls=[
                                ToolCallDelta(
                                    index=event.output_index,
                                    call_id=item.call_id,
                                    name=item.name,
                                )
                            ],
                        )
                    continue

                if event_type == "response.function_call_arguments.delta":
                    state = tool_call_state.get(event.output_index)
                    if state:
                        state["args_seen"] = True
                        yield ChunkResponse(
                            content="",
                            reasoning=None,
                            tool_calls=[
                                ToolCallDelta(
                                    index=event.output_index,
                                    arguments_delta=event.delta,
                                )
                            ],
                        )
                    continue

                if event_type == "response.function_call_arguments.done":
                    state = tool_call_state.get(event.output_index)
                    if state and not state.get("args_seen"):
                        yield ChunkResponse(
                            content="",
                            reasoning=None,
                            tool_calls=[
                                ToolCallDelta(
                                    index=event.output_index,
                                    arguments_delta=event.arguments,
                                )
                            ],
                        )
                    continue

                if event_type == "response.completed":
                    response = event.response
                    for idx, item in enumerate(response.output or []):
                        if getattr(item, "type", None) != "function_call":
                            continue
                        state = tool_call_state.get(idx)
                        if not state or not state.get("emitted"):
                            yield ChunkResponse(
                                content="",
                                reasoning=None,
                                tool_calls=[
                                    ToolCallDelta(
                                        index=idx,
                                        call_id=item.call_id,
                                        name=item.name,
                                    )
                                ],
                            )
                            tool_call_state[idx] = {
                                "call_id": item.call_id,
                                "name": item.name,
                                "args_seen": False,
                                "emitted": True,
                            }
                            state = tool_call_state[idx]

                        if not state.get("args_seen"):
                            yield ChunkResponse(
                                content="",
                                reasoning=None,
                                tool_calls=[
                                    ToolCallDelta(
                                        index=idx,
                                        arguments_delta=item.arguments,
                                    )
                                ],
                            )
                            state["args_seen"] = True

                    token_usage = self._create_token_usage(response.usage)
                    yield ChunkResponse(content="", reasoning=None, is_complete=True, usage=token_usage)

            self.add_assistant_message(
                accumulated_content,
                reasoning_content=accumulated_reasoning if accumulated_reasoning else None,
            )
            logger.info(f"Completed streaming response from {self.model.provider.value} Responses API")

        except Exception as e:
            logger.error(f"Error in {self.model.provider.value} Responses API streaming: {str(e)}")
            raise ValueError(f"Error in {self.model.provider.value} Responses API streaming: {str(e)}")

    async def cleanup(self):
        await super().cleanup()
