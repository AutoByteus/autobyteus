# file: autobyteus/autobyteus/tools/usage/parsers/base_parser.py
import logging
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent.tool_invocation import ToolInvocation
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class BaseToolUsageParser(ABC):
    """
    Abstract base class for parsing tool usage from an LLM's response text.
    These parsers are responsible for extracting structured tool call information.
    """

    def get_name(self) -> str:
        """
        Returns the unique name for this parser.
        Defaults to the class name.
        """
        return self.__class__.__name__

    @abstractmethod
    def parse(self, response: 'CompleteResponse') -> List['ToolInvocation']:
        """
        Parses the LLM's response. If actionable tool calls are found,
        this method should return a list of ToolInvocation objects.

        Args:
            response: The CompleteResponse object from the LLM.

        Returns:
            A list of ToolInvocation objects. Returns an empty list if no
            valid tool calls are found.
        """
        raise NotImplementedError("Subclasses must implement the 'parse' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
