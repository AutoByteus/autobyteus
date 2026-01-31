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


class OpenAIChatRenderer(BasePromptRenderer):
    async def render(self, messages: List[Message]) -> List[Dict[str, Any]]:
        rendered: List[Dict[str, Any]] = []

        for msg in messages:
            content: Any = msg.content
            if msg.image_urls or msg.audio_urls or msg.video_urls:
                content_parts: List[Dict[str, Any]] = []
                if msg.content:
                    content_parts.append({"type": "text", "text": msg.content})

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
                        content_parts.append(create_data_uri(mime_type, b64_image))
                except Exception as e:
                    logger.error("Error processing one or more images: %s", e)

                if msg.audio_urls:
                    logger.warning("OpenAI compatible layer does not yet support audio; skipping.")
                if msg.video_urls:
                    logger.warning("OpenAI compatible layer does not yet support video; skipping.")

                content = content_parts

            if isinstance(msg.tool_payload, ToolCallPayload):
                tool_calls = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments, ensure_ascii=True),
                        },
                    }
                    for call in msg.tool_payload.tool_calls
                ]
                rendered.append(
                    {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls,
                    }
                )
                continue

            if isinstance(msg.tool_payload, ToolResultPayload):
                result_text = _format_tool_result(msg.tool_payload)
                rendered.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_payload.tool_call_id,
                        "content": result_text,
                    }
                )
                continue

            rendered.append({"role": msg.role.value, "content": content})

        return rendered


def _format_tool_result(payload: ToolResultPayload) -> str:
    if payload.tool_error:
        return f"Error: {payload.tool_error}"
    if payload.tool_result is None:
        return ""
    if isinstance(payload.tool_result, (dict, list)):
        return json.dumps(payload.tool_result, ensure_ascii=True)
    return str(payload.tool_result)
