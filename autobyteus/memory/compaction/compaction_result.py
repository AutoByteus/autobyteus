from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CompactionResult:
    episodic_summary: str
    semantic_facts: List[Dict[str, Any]] = field(default_factory=list)
