import asyncio
import logging
from typing import Dict, List, Any, Optional

from ollama import Image

from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.utils.messages import Message, MessageRole, ToolCallPayload, ToolResultPayload
from autobyteus.llm.utils.media_payload_formatter import media_source_to_base64

logger = logging.getLogger(__name__)


class OllamaPromptRenderer(BasePromptRenderer):
    async def render(self, messages: List[Message]) -> List[Dict[str, Any]]:
        formatted_messages: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.role.value
            content = msg.content or ""
            if msg.tool_payload or msg.role == MessageRole.TOOL:
                content = _format_tool_payload(msg) or ""
                role = (
                    MessageRole.USER.value
                    if msg.role == MessageRole.TOOL
                    else MessageRole.ASSISTANT.value
                )
            msg_dict: Dict[str, Any] = {"role": role, "content": content}

            if msg.image_urls:
                try:
                    image_tasks = [media_source_to_base64(url) for url in msg.image_urls]
                    prepared_base64_images = await asyncio.gather(*image_tasks)
                    if prepared_base64_images:
                        msg_dict["images"] = [Image(value=b64_string) for b64_string in prepared_base64_images]
                except Exception as exc:
                    logger.error("Error processing images for Ollama, skipping them. Error: %s", exc)

            formatted_messages.append(msg_dict)
        return formatted_messages


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
