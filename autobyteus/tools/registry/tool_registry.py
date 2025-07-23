# file: autobyteus/tools/registry/tool_registry.py
import logging
from typing import Dict, List, Optional, Type, TYPE_CHECKING
from collections import defaultdict

from autobyteus.tools.registry.tool_definition import ToolDefinition
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_origin import ToolOrigin

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolRegistry(metaclass=SingletonMeta):
    """
    Manages ToolDefinitions and creates tool instances. It can create instances
    from a tool_class or by using a custom_factory provided in the definition.
    """
    _definitions: Dict[str, ToolDefinition] = {}

    def __init__(self):
        """
        Initializes the ToolRegistry.
        """
        logger.info("ToolRegistry initialized.")

    def register_tool(self, definition: ToolDefinition):
        """
        Registers a tool definition.

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

    def unregister_tool(self, name: str) -> bool:
        """
        Unregisters a tool definition by its name.

        Args:
            name: The unique name of the tool definition to unregister.

        Returns:
            True if the tool was found and unregistered, False otherwise.
        """
        if name in self._definitions:
            del self._definitions[name]
            logger.info(f"Successfully unregistered tool definition: '{name}'")
            return True
        else:
            logger.warning(f"Attempted to unregister tool '{name}', but it was not found in the registry.")
            return False

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
        Creates a tool instance using its definition and injects the definition
        back into the instance.
        """
        definition = self.get_tool_definition(name)
        if not definition:
            logger.error(f"Cannot create tool: No definition found for name '{name}'")
            raise ValueError(f"No tool definition found for name '{name}'")
        
        try:
            tool_instance: 'BaseTool'
            if definition.custom_factory:
                logger.info(f"Creating tool instance for '{name}' using its custom factory.")
                tool_instance = definition.custom_factory(config)
            elif definition.tool_class:
                logger.info(f"Creating tool instance for '{name}' using class '{definition.tool_class.__name__}' and passing ToolConfig.")
                tool_instance = definition.tool_class(config=config)
            else:
                raise ValueError(f"ToolDefinition for '{name}' is invalid: missing both tool_class and custom_factory.")

            # Inject the definition into the newly created instance.
            tool_instance.definition = definition
            logger.debug(f"Injected ToolDefinition into instance of '{name}'.")

            return tool_instance

        except Exception as e:
            creator_type = "factory" if definition.custom_factory else f"class '{definition.tool_class.__name__}'"
            logger.error(f"Failed to create tool instance for '{name}' using {creator_type}: {e}", exc_info=True)
            raise TypeError(f"Failed to create tool '{name}': {e}") from e

    def list_tools(self) -> List[ToolDefinition]:
        """
        Returns a list of all registered tool definitions.
        """
        return list(self._definitions.values())

    def list_tool_names(self) -> List[str]:
        """
        Returns a list of the names of all registered tools.
        """
        return list(self._definitions.keys())

    def get_all_definitions(self) -> Dict[str, ToolDefinition]:
        """Returns the internal dictionary of definitions."""
        return dict(ToolRegistry._definitions)
        
    def get_tools_by_mcp_server(self, server_id: str) -> List[ToolDefinition]:
        """
        Returns a list of all registered tool definitions that originated
        from a specific MCP server.

        Args:
            server_id: The unique ID of the MCP server to query for.

        Returns:
            A list of matching ToolDefinition objects.
        """
        if not server_id:
            return []
        
        return [
            td for td in self._definitions.values()
            if td.origin == ToolOrigin.MCP and td.metadata.get("mcp_server_id") == server_id
        ]

    def get_tools_by_category(self, category: str) -> List[ToolDefinition]:
        """
        Returns a list of all registered tool definitions that match a specific category.

        Args:
            category: The category string to filter by.

        Returns:
            A list of matching ToolDefinition objects, sorted by name.
        """
        if not category:
            return []
        
        matching_tools = [
            td for td in self._definitions.values() if td.category == category
        ]
        return sorted(matching_tools, key=lambda td: td.name)

    def get_tools_grouped_by_category(self, origin: Optional[ToolOrigin] = None) -> Dict[str, List[ToolDefinition]]:
        """
        Returns all registered tool definitions, grouped into a dictionary by their category.
        Can optionally filter by tool origin before grouping.

        Args:
            origin: If provided, only tools from this origin will be included.

        Returns:
            A dictionary where keys are category strings and values are lists
            of ToolDefinition objects belonging to that category. Both the categories
            and the tools within each category are sorted alphabetically.
        """
        grouped_tools = defaultdict(list)
        
        tools_to_process = self._definitions.values()
        if origin:
            tools_to_process = [td for td in tools_to_process if td.origin == origin]

        for td in tools_to_process:
            grouped_tools[td.category].append(td)
        
        # Sort tools within each category and sort the categories themselves for deterministic output
        sorted_grouped_tools = {}
        for category in sorted(grouped_tools.keys()):
            sorted_grouped_tools[category] = sorted(grouped_tools[category], key=lambda td: td.name)
            
        return sorted_grouped_tools

default_tool_registry = ToolRegistry()
