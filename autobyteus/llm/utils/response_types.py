
from dataclasses import dataclass
from typing import Optional
from autobyteus.llm.utils.token_usage import TokenUsage

@dataclass
class CompleteResponse:
    content: str
    usage: Optional[TokenUsage] = None

    @classmethod
    def from_content(cls, content: str) -> 'CompleteResponse':
        return cls(content=content)

@dataclass
class ChunkResponse:
    content: str  # The actual content/text of the chunk
    is_complete: bool = False  # Indicates if this is the final chunk
    usage: Optional[TokenUsage] = None  # Token usage stats, typically available in final chunk
