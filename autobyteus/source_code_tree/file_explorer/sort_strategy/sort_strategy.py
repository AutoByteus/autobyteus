# autobyteus/source_code_tree/file_explorer/sort_strategy/sort_strategy.py

from abc import ABC, abstractmethod
from typing import List


class SortStrategy(ABC):
    """
    Base class for all sort strategies.
    """
    
    @abstractmethod
    def sort(self, paths: List[str]) -> List[str]:
        pass
