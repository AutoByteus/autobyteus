from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from autobyteus.memory.models.memory_types import MemoryType


class MemoryStore(ABC):
    @abstractmethod
    def add(self, items: Iterable[object]) -> None:
        raise NotImplementedError

    @abstractmethod
    def list(self, memory_type: MemoryType, limit: Optional[int] = None) -> List[object]:
        raise NotImplementedError
