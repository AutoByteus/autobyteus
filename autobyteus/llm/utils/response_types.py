from dataclasses import dataclass, field
from typing import Optional, List
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta

@dataclass
class CompleteResponse:
    content: str
    reasoning: Optional[str] = None
    usage: Optional[TokenUsage] = None
    image_urls: List[str] = field(default_factory=list)
    audio_urls: List[str] = field(default_factory=list)
    video_urls: List[str] = field(default_factory=list)

    @classmethod
    def from_content(cls, content: str) -> 'CompleteResponse':
        return cls(content=content)

@dataclass
class ChunkResponse:
    content: str  # The actual content/text of the chunk
    reasoning: Optional[str] = None
    is_complete: bool = False  # Indicates if this is the final chunk
    usage: Optional[TokenUsage] = None  # Token usage stats, typically available in final chunk
    image_urls: List[str] = field(default_factory=list)
    audio_urls: List[str] = field(default_factory=list)
    video_urls: List[str] = field(default_factory=list)
    tool_calls: Optional[List[ToolCallDelta]] = None  # API-provided tool call deltas

