# file: autobyteus/autobyteus/tools/usage/formatters/base_formatter.py
from abc import ABC, abstractmethod
from typing import Union, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class BaseSchemaFormatter(ABC):
    """
    Abstract base class for formatting the schema of a single tool
    into a provider-specific format.
    """
    @abstractmethod
    def provide(self, tool_definition: 'ToolDefinition') -> Union[str, Dict]:
        """
        Formats the schema of the given tool definition.

        Args:
            tool_definition: The tool definition to format.

        Returns:
            An XML string or a dictionary representing the tool's schema.
        """
        pass

class BaseExampleFormatter(ABC):
    """
    Abstract base class for formatting a usage example of a single tool
    into a provider-specific format.
    """
    @abstractmethod
    def provide(self, tool_definition: 'ToolDefinition') -> Union[str, Dict]:
        """
        Formats a usage example for the given tool definition.

        Args:
            tool_definition: The tool definition to format an example for.

        Returns:
            An XML string or a dictionary representing a tool usage example.
        """
        pass
