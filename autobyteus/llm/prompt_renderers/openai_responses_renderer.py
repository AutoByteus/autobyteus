import asyncio
import json
import logging
from typing import List, Dict, Any

from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.utils.media_payload_formatter import (
    media_source_to_base64,
    create_data_uri,
    get_mime_type,
    is_valid_media_path,
)
from autobyteus.llm.utils.messages import Message, ToolCallPayload, ToolResultPayload

logger = logging.getLogger(__name__)


class OpenAIResponsesRenderer(BasePromptRenderer):
    async def render(self, messages: List[Message]) -> List[Dict[str, Any]]:
        rendered: List[Dict[str, Any]] = []

        for msg in messages:
            if isinstance(msg.tool_payload, ToolCallPayload):
                rendered.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": _format_tool_calls(msg.tool_payload),
                    }
                )
                continue

            if isinstance(msg.tool_payload, ToolResultPayload):
                rendered.append(
                    {
                        "type": "message",
                        "role": "user",
                        "content": _format_tool_result(msg.tool_payload),
                    }
                )
                continue

            if msg.image_urls or msg.audio_urls or msg.video_urls:
                content_parts: List[Dict[str, Any]] = []
                if msg.content:
                    content_parts.append({"type": "input_text", "text": msg.content})

                image_tasks = []
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
                            {"type": "input_image", "image_url": data_uri, "detail": "auto"}
                        )
                except Exception as e:
                    logger.error("Error processing one or more images: %s", e)

                if msg.audio_urls:
                    logger.warning("OpenAI Responses input does not yet support audio; skipping.")
                if msg.video_urls:
                    logger.warning("OpenAI Responses input does not yet support video; skipping.")

                rendered.append(
                    {"type": "message", "role": msg.role.value, "content": content_parts}
                )
            else:
                rendered.append(
                    {"type": "message", "role": msg.role.value, "content": msg.content or ""}
                )

        return rendered


def _format_tool_calls(payload: ToolCallPayload) -> str:
    lines = []
    for call in payload.tool_calls:
        args = json.dumps(call.arguments, ensure_ascii=True)
        lines.append(f"[TOOL_CALL] {call.name} {args}")
    return "\n".join(lines)


def _format_tool_result(payload: ToolResultPayload) -> str:
    if payload.tool_error:
        return f"[TOOL_ERROR] {payload.tool_name} {payload.tool_error}"
    if payload.tool_result is None:
        return f"[TOOL_RESULT] {payload.tool_name}"
    if isinstance(payload.tool_result, (dict, list)):
        result_text = json.dumps(payload.tool_result, ensure_ascii=True)
    else:
        result_text = str(payload.tool_result)
    return f"[TOOL_RESULT] {payload.tool_name} {result_text}"
