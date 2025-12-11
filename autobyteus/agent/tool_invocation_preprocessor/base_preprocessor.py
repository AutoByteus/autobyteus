import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .processor_meta import ToolInvocationPreprocessorMeta

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)


class BaseToolInvocationPreprocessor(ABC, metaclass=ToolInvocationPreprocessorMeta):
    """
    Pre-execution processors that can mutate or validate a ToolInvocation
    before the tool is executed.
    """

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__

    @classmethod
    def get_order(cls) -> int:
        """Lower numbers run earlier."""
        return 500

    @classmethod
    def is_mandatory(cls) -> bool:
        return False

    @abstractmethod
    async def process(self,
                      invocation: 'ToolInvocation',
                      context: 'AgentContext') -> 'ToolInvocation':
        """
        Process and return the (potentially modified) ToolInvocation.
        May raise to signal failure; caller should handle and surface as tool error.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

