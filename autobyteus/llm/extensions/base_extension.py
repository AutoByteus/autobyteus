from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING, Any

from autobyteus.llm.utils.messages import Message
from autobyteus.llm.utils.response_types import CompleteResponse

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

class LLMExtension(ABC):
    def __init__(self, llm: 'BaseLLM'):
        self.llm = llm

    @abstractmethod
    async def before_invoke(
        self, messages: List[Message], rendered_payload: Optional[Any] = None, **kwargs
    ) -> None:
        """
        Called before invoking the LLM with explicit messages.
        """
        pass

    @abstractmethod
    async def after_invoke(
        self, messages: List[Message], response: CompleteResponse = None, **kwargs
    ) -> None:
        """
        Called after receiving the response from the LLM.
        
        Args:
            messages: The explicit prompt messages used for invocation.
            response: Complete response including content and usage information.
            kwargs: Additional arguments.
        """
        pass

    async def cleanup(self) -> None:
        pass
