from dataclasses import dataclass
from typing import Dict, Union, List, Optional, Any
from enum import Enum

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class ToolCallSpec:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolCallPayload:
    tool_calls: List[ToolCallSpec]


@dataclass
class ToolResultPayload:
    tool_call_id: str
    tool_name: str
    tool_result: Any
    tool_error: Optional[str] = None


ToolPayload = Union[ToolCallPayload, ToolResultPayload]


class Message:
    def __init__(self,
                 role: MessageRole,
                 content: Optional[str] = None,
                 reasoning_content: Optional[str] = None,
                 image_urls: Optional[List[str]] = None,
                 audio_urls: Optional[List[str]] = None,
                 video_urls: Optional[List[str]] = None,
                 tool_payload: Optional[ToolPayload] = None):
        """
        Initializes a rich Message object for conversation history.

        Args:
            role: The role of the message originator.
            content: The textual content of the message.
            reasoning_content: Optional reasoning/thought process from an assistant.
            image_urls: Optional list of image URIs.
            audio_urls: Optional list of audio URIs.
            video_urls: Optional list of video URIs.
            tool_payload: Optional tool payload (tool calls or tool result).
        """
        self.role = role
        self.content = content
        self.reasoning_content = reasoning_content
        self.image_urls = image_urls or []
        self.audio_urls = audio_urls or []
        self.video_urls = video_urls or []
        self.tool_payload = tool_payload

    def _serialize_tool_payload(self) -> Optional[Dict[str, Any]]:
        if self.tool_payload is None:
            return None
        if isinstance(self.tool_payload, ToolCallPayload):
            return {
                "tool_calls": [
                    {
                        "id": call.id,
                        "name": call.name,
                        "arguments": call.arguments,
                    }
                    for call in self.tool_payload.tool_calls
                ]
            }
        if isinstance(self.tool_payload, ToolResultPayload):
            return {
                "tool_call_id": self.tool_payload.tool_call_id,
                "tool_name": self.tool_payload.tool_name,
                "tool_result": self.tool_payload.tool_result,
                "tool_error": self.tool_payload.tool_error,
            }
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns a simple dictionary representation of the Message object.
        This is for internal use and does not format for any specific API.
        """
        return {
            "role": self.role.value,
            "content": self.content,
            "reasoning_content": self.reasoning_content,
            "image_urls": self.image_urls,
            "audio_urls": self.audio_urls,
            "video_urls": self.video_urls,
            "tool_payload": self._serialize_tool_payload(),
        }
