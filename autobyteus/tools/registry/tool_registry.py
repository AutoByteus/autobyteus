# file: autobyteus/autobyteus/tools/registry/tool_registry.py
import logging
from typing import Dict, List, Optional

from autobyteus.tools.registry.tool_definition import ToolDefinition
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.tools.factory.tool_factory import ToolFactory


logger = logging.getLogger(__name__)

class ToolRegistry(metaclass=SingletonMeta):
    """
    Manages ToolDefinitions (name, description, tool_class), populated exclusively via
    programmatic registration. Uses ToolFactory to create tool instances.
    """
    _definitions: Dict[str, ToolDefinition] = {}

    def __init__(self, tool_factory: ToolFactory):
        """
        Initializes the ToolRegistry with a ToolFactory.

        Args:
            tool_factory: The ToolFactory instance used to create tool instances.
        """
        self.tool_factory = tool_factory
        logger.info("ToolRegistry initialized with ToolFactory.")

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
        logger.info(f"Successfully registered tool definition: '{tool_name}'")

    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        """
        Retrieves the definition for a specific tool name.

        Args:
            name: The unique name of the tool definition to retrieve.

        Returns:
            The ToolDefinition object (name, description, tool_class) if found, otherwise None.
        """
        definition = self._definitions.get(name)
        if not definition:
            logger.debug(f"Tool definition not found for name: '{name}'")
        return definition

    def create_tool(self, name: str):
        """
        Creates a tool instance using the ToolFactory based on the tool definition.

        Args:
            name: The name of the tool to create.

        Returns:
            The tool instance if the definition exists, otherwise None.

        Raises:
            ValueError: If the tool definition is not found.
        """
        definition = self.get_tool_definition(name)
        if not definition:
            logger.error(f"Cannot create tool: No definition found for name '{name}'")
            raise ValueError(f"No tool definition found for name '{name}'")
        
        logger.info(f"Creating tool instance for '{name}' using ToolFactory")
        return self.tool_factory.create_tool(name)

    def list_tools(self) -> List[ToolDefinition]:
        """
        Returns a list of all registered tool definitions.

        Returns:
            A list of ToolDefinition objects (name, description, tool_class).
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

default_tool_registry = ToolRegistry(tool_factory=ToolFactory())
