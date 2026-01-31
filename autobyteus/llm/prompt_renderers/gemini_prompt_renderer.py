import base64
import mimetypes
import logging
from typing import Dict, List, Any, Optional

from google.genai import types as genai_types

from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.utils.messages import Message, MessageRole, ToolCallPayload, ToolResultPayload
from autobyteus.llm.utils.media_payload_formatter import media_source_to_base64, get_mime_type

logger = logging.getLogger(__name__)


class GeminiPromptRenderer(BasePromptRenderer):
    async def render(self, messages: List[Message]) -> List[Dict[str, Any]]:
        history: List[Dict[str, Any]] = []
        for msg in messages:
            role = None
            content_text = msg.content
            if msg.tool_payload or msg.role == MessageRole.TOOL:
                content_text = _format_tool_payload(msg)
                role = "model" if msg.role == MessageRole.ASSISTANT else "user"
            elif msg.role in (MessageRole.USER, MessageRole.ASSISTANT):
                role = "model" if msg.role == MessageRole.ASSISTANT else "user"
            else:
                continue

            if role is None:
                continue

            parts: List[Any] = []
            if content_text:
                parts.append({"text": content_text})

            media_urls = msg.image_urls + msg.audio_urls + msg.video_urls
            for url in media_urls:
                try:
                    b64_data = await media_source_to_base64(url)
                    data_bytes = base64.b64decode(b64_data)
                    mime_type, _ = mimetypes.guess_type(url)
                    if not mime_type:
                        mime_type = get_mime_type(url)
                    parts.append(genai_types.Part.from_bytes(data=data_bytes, mime_type=mime_type))
                except Exception as exc:
                    logger.error("Failed to process media content %s: %s", url, exc)

            if parts:
                history.append({"role": role, "parts": parts})

        return history


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
