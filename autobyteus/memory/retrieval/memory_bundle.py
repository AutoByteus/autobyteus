from dataclasses import dataclass, field
from typing import List

from autobyteus.memory.models.episodic_item import EpisodicItem
from autobyteus.memory.models.semantic_item import SemanticItem


@dataclass
class MemoryBundle:
    episodic: List[EpisodicItem] = field(default_factory=list)
    semantic: List[SemanticItem] = field(default_factory=list)
