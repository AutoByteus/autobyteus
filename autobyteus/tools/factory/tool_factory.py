# file: autobyteus/autobyteus/tools/factory/tool_factory.py
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.tools.tool_config import ToolConfig

class ToolFactory(ABC):
    """
    Abstract base class for all tool factories.
    
    A tool factory is a class responsible for creating instances of a specific tool,
    often with pre-configured settings provided during the factory's own
    initialization.
    """

    @abstractmethod
    def create_tool(self, config: Optional['ToolConfig'] = None) -> 'BaseTool':
        """
        Creates and returns a configured instance of a tool.

        Args:
            config: An optional ToolConfig object that can provide additional,
                    instance-specific configuration at creation time. This may
                    or may not be used by the factory, depending on its design.

        Returns:
            An instance of a class derived from BaseTool.
        """
        pass
