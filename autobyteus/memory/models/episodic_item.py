from dataclasses import dataclass, field
from typing import Any, Dict, List

from .memory_types import MemoryType


@dataclass
class EpisodicItem:
    id: str
    ts: float
    turn_ids: List[str]
    summary: str
    tags: List[str] = field(default_factory=list)
    salience: float = 0.0

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.EPISODIC

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "ts": self.ts,
            "turn_ids": self.turn_ids,
            "summary": self.summary,
            "salience": self.salience,
        }
        if self.tags:
            data["tags"] = self.tags
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpisodicItem":
        return cls(
            id=data["id"],
            ts=data["ts"],
            turn_ids=data.get("turn_ids", []),
            summary=data.get("summary", ""),
            tags=data.get("tags", []),
            salience=data.get("salience", 0.0),
        )
