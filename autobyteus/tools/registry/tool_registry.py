# file: autobyteus/autobyteus/tools/registry/tool_registry.py
import logging
from typing import Dict, List, Optional, Type, TYPE_CHECKING

from autobyteus.tools.registry.tool_definition import ToolDefinition
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.tools.tool_config import ToolConfig

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolRegistry(metaclass=SingletonMeta):
    """
    Manages ToolDefinitions (name, description, tool_class), populated exclusively via
    programmatic registration. Creates tool instances using class constructors and ToolConfig.
    """
    _definitions: Dict[str, ToolDefinition] = {}

    def __init__(self):
        """
        Initializes the ToolRegistry.
        """
        logger.info("ToolRegistry initialized.")

    def register_tool(self, definition: ToolDefinition):
        """
        Registers a tool definition (name, description, tool_class) programmatically.

        Args:
            definition: The ToolDefinition object to register.

        Raises:
            ValueError: If the definition is invalid. Overwrites existing definitions with the same name.
        """
        if not isinstance(definition, ToolDefinition):
            raise ValueError("Attempted to register an object that is not a ToolDefinition.")

        tool_name = definition.name
        if tool_name in self._definitions:
            logger.warning(f"Overwriting existing tool definition for name: '{tool_name}'")
        ToolRegistry._definitions[tool_name] = definition
        logger.info(f"Successfully registered tool definition: '{tool_name}' with class '{definition.tool_class.__name__}'")

    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        """
        Retrieves the definition for a specific tool name.

        Args:
            name: The unique name of the tool definition to retrieve.

        Returns:
            The ToolDefinition object if found, otherwise None.
        """
        definition = self._definitions.get(name)
        if not definition:
            logger.debug(f"Tool definition not found for name: '{name}'")
        return definition

    def create_tool(self, name: str, config: Optional[ToolConfig] = None) -> 'BaseTool':
        """
        Creates a tool instance using the class constructor and optional ToolConfig.

        Args:
            name: The name of the tool to create.
            config: Optional ToolConfig with constructor parameters.

        Returns:
            The tool instance if the definition exists.

        Raises:
            ValueError: If the tool definition is not found.
            TypeError: If tool instantiation fails.
        """
        definition = self.get_tool_definition(name)
        if not definition:
            logger.error(f"Cannot create tool: No definition found for name '{name}'")
            raise ValueError(f"No tool definition found for name '{name}'")
        
        tool_class = definition.tool_class
        
        # Prepare constructor arguments from config
        constructor_kwargs = {}
        if config:
            constructor_kwargs = config.get_constructor_kwargs()
        
        try:
            logger.info(f"Creating tool instance for '{name}' using class '{tool_class.__name__}' with config: {constructor_kwargs}")
            tool_instance = tool_class(**constructor_kwargs)
            logger.debug(f"Successfully created tool instance for '{name}'")
            return tool_instance
        except Exception as e:
            logger.error(f"Failed to create tool instance for '{name}': {e}", exc_info=True)
            raise TypeError(f"Failed to create tool '{name}' with class '{tool_class.__name__}': {e}")

    def list_tools(self) -> List[ToolDefinition]:
        """
        Returns a list of all registered tool definitions.

        Returns:
            A list of ToolDefinition objects.
        """
        return list(self._definitions.values())

    def list_tool_names(self) -> List[str]:
        """
        Returns a list of the names of all registered tools.

        Returns:
            A list of tool name strings.
        """
        return list(self._definitions.keys())

    def get_all_definitions(self) -> Dict[str, ToolDefinition]:
        """Returns the internal dictionary of definitions."""
        return dict(ToolRegistry._definitions)

default_tool_registry = ToolRegistry()
