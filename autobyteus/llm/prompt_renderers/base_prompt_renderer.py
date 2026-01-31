from abc import ABC, abstractmethod
from typing import List, Dict, Any

from autobyteus.llm.utils.messages import Message


class BasePromptRenderer(ABC):
    @abstractmethod
    async def render(self, messages: List[Message]) -> List[Dict[str, Any]]:
        raise NotImplementedError
