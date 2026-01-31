from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .memory_types import MemoryType


@dataclass
class RawTraceItem:
    id: str
    ts: float
    turn_id: str
    seq: int
    trace_type: str
    content: str
    source_event: str
    media: Optional[Dict[str, List[str]]] = None
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    tool_error: Optional[str] = None
    correlation_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    tool_result_ref: Optional[str] = None

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.RAW_TRACE

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "ts": self.ts,
            "turn_id": self.turn_id,
            "seq": self.seq,
            "trace_type": self.trace_type,
            "content": self.content,
            "source_event": self.source_event,
        }
        if self.media is not None:
            data["media"] = self.media
        if self.tool_name is not None:
            data["tool_name"] = self.tool_name
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        if self.tool_args is not None:
            data["tool_args"] = self.tool_args
        if self.tool_result is not None:
            data["tool_result"] = self.tool_result
        if self.tool_error is not None:
            data["tool_error"] = self.tool_error
        if self.correlation_id is not None:
            data["correlation_id"] = self.correlation_id
        if self.tags:
            data["tags"] = self.tags
        if self.tool_result_ref is not None:
            data["tool_result_ref"] = self.tool_result_ref
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawTraceItem":
        return cls(
            id=data["id"],
            ts=data["ts"],
            turn_id=data["turn_id"],
            seq=data["seq"],
            trace_type=data["trace_type"],
            content=data.get("content", ""),
            source_event=data["source_event"],
            media=data.get("media"),
            tool_name=data.get("tool_name"),
            tool_call_id=data.get("tool_call_id"),
            tool_args=data.get("tool_args"),
            tool_result=data.get("tool_result"),
            tool_error=data.get("tool_error"),
            correlation_id=data.get("correlation_id"),
            tags=data.get("tags", []),
            tool_result_ref=data.get("tool_result_ref"),
        )
