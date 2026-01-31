from dataclasses import dataclass, field
from typing import Any, Dict, List

from .memory_types import MemoryType


@dataclass
class SemanticItem:
    id: str
    ts: float
    fact: str
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    salience: float = 0.0

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.SEMANTIC

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "ts": self.ts,
            "fact": self.fact,
            "confidence": self.confidence,
            "salience": self.salience,
        }
        if self.tags:
            data["tags"] = self.tags
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticItem":
        return cls(
            id=data["id"],
            ts=data["ts"],
            fact=data.get("fact", ""),
            tags=data.get("tags", []),
            confidence=data.get("confidence", 0.0),
            salience=data.get("salience", 0.0),
        )
