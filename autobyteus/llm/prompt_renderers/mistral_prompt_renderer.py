import asyncio
import logging
from typing import Dict, List, Any, Optional, Union

from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.utils.messages import Message, MessageRole, ToolCallPayload, ToolResultPayload
from autobyteus.llm.utils.media_payload_formatter import (
    media_source_to_base64,
    get_mime_type,
    is_valid_media_path,
)

logger = logging.getLogger(__name__)


class MistralPromptRenderer(BasePromptRenderer):
    async def render(self, messages: List[Message]) -> List[Dict[str, Any]]:
        mistral_messages: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.role.value
            if msg.tool_payload or msg.role == MessageRole.TOOL:
                content_text = _format_tool_payload(msg) or ""
                role = (
                    MessageRole.USER.value
                    if msg.role == MessageRole.TOOL
                    else MessageRole.ASSISTANT.value
                )
                msg = Message(
                    role=MessageRole.USER
                    if role == MessageRole.USER.value
                    else MessageRole.ASSISTANT,
                    content=content_text,
                )

            if not msg.content and not msg.image_urls and msg.role != MessageRole.SYSTEM:
                continue

            content: Union[str, List[Dict[str, Any]]]
            if msg.image_urls:
                content_parts: List[Dict[str, Any]] = []
                if msg.content:
                    content_parts.append({"type": "text", "text": msg.content})

                image_tasks = [media_source_to_base64(url) for url in msg.image_urls]
                try:
                    base64_images = await asyncio.gather(*image_tasks)
                    for i, b64_image in enumerate(base64_images):
                        original_url = msg.image_urls[i]
                        mime_type = (
                            get_mime_type(original_url)
                            if is_valid_media_path(original_url)
                            else "image/jpeg"
                        )
                        data_uri = f"data:{mime_type};base64,{b64_image}"
                        content_parts.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": data_uri},
                            }
                        )
                except Exception as exc:
                    logger.error("Error processing images for Mistral: %s", exc)

                if msg.audio_urls:
                    logger.warning("MistralLLM does not yet support audio; skipping.")
                if msg.video_urls:
                    logger.warning("MistralLLM does not yet support video; skipping.")

                content = content_parts
            else:
                content = msg.content or ""

            mistral_messages.append({"role": role, "content": content})

        return mistral_messages


def _format_tool_payload(message: Message) -> Optional[str]:
    payload = message.tool_payload
    if isinstance(payload, ToolCallPayload):
        lines = [f"[TOOL_CALL] {call.name} {call.arguments}" for call in payload.tool_calls]
        return "\n".join(lines)
    if isinstance(payload, ToolResultPayload):
        if payload.tool_error:
            return f"[TOOL_ERROR] {payload.tool_name} {payload.tool_error}"
        return f"[TOOL_RESULT] {payload.tool_name} {payload.tool_result}"
    return None
