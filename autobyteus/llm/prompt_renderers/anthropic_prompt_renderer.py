import asyncio
import json
import logging
from typing import List, Dict, Any

from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.utils.media_payload_formatter import (
    media_source_to_base64,
    get_mime_type,
    is_valid_media_path,
)
from autobyteus.llm.utils.messages import Message, MessageRole, ToolCallPayload, ToolResultPayload

logger = logging.getLogger(__name__)


class AnthropicPromptRenderer(BasePromptRenderer):
    async def render(self, messages: List[Message]) -> List[Dict[str, Any]]:
        formatted_messages: List[Dict[str, Any]] = []
        valid_image_mimes = {"image/jpeg", "image/png", "image/gif", "image/webp"}

        for msg in messages:
            role = msg.role.value
            if msg.tool_payload or msg.role == MessageRole.TOOL:
                payload_text = _format_tool_payload(msg)
                role = (
                    MessageRole.USER.value
                    if msg.role == MessageRole.TOOL
                    else MessageRole.ASSISTANT.value
                )
                msg = Message(
                    role=MessageRole.USER
                    if role == MessageRole.USER.value
                    else MessageRole.ASSISTANT,
                    content=payload_text or "",
                )

            if msg.image_urls:
                content_blocks: List[Dict[str, Any]] = []

                image_tasks = [media_source_to_base64(url) for url in msg.image_urls]
                try:
                    base64_images = await asyncio.gather(*image_tasks)

                    for i, b64_data in enumerate(base64_images):
                        original_url = msg.image_urls[i]
                        mime_type = get_mime_type(original_url)

                        if mime_type not in valid_image_mimes:
                            logger.warning(
                                "Unsupported image MIME type '%s' for %s. "
                                "Anthropic supports: %s. Defaulting to image/jpeg.",
                                mime_type,
                                original_url,
                                valid_image_mimes,
                            )
                            mime_type = "image/jpeg"

                        content_blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64_data,
                                },
                            }
                        )
                except Exception as e:
                    logger.error("Error processing images for Claude: %s", e)

                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})

                formatted_messages.append({"role": role, "content": content_blocks})
            else:
                formatted_messages.append(
                    {
                        "role": role,
                        "content": msg.content or "",
                    }
                )

        return formatted_messages


def _format_tool_payload(message: Message) -> str:
    payload = message.tool_payload
    if isinstance(payload, ToolCallPayload):
        lines = []
        for call in payload.tool_calls:
            args = call.arguments
            if isinstance(args, (dict, list)):
                args = json.dumps(args, ensure_ascii=True)
            lines.append(f"[TOOL_CALL] {call.name} {args}")
        return "\n".join(lines)
    if isinstance(payload, ToolResultPayload):
        if payload.tool_error:
            return f"[TOOL_ERROR] {payload.tool_name} {payload.tool_error}"
        result = payload.tool_result
        if isinstance(result, (dict, list)):
            result = json.dumps(result, ensure_ascii=True)
        return f"[TOOL_RESULT] {payload.tool_name} {result}"
    return message.content or ""
