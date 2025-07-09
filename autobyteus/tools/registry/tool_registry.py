# file: autobyteus/tools/registry/tool_registry.py
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
        Creates a tool instance using its definition, either from a factory or a class.

        Args:
            name: The name of the tool to create.
            config: Optional ToolConfig with constructor parameters for class-based tools
                    or to be passed to a custom factory.

        Returns:
            The tool instance if the definition exists.

        Raises:
            ValueError: If the tool definition is not found or is invalid.
            TypeError: If tool instantiation fails.
        """
        definition = self.get_tool_definition(name)
        if not definition:
            logger.error(f"Cannot create tool: No definition found for name '{name}'")
            raise ValueError(f"No tool definition found for name '{name}'")
        
        try:
            # Prefer the custom factory if it exists
            if definition.custom_factory:
                logger.info(f"Creating tool instance for '{name}' using its custom factory.")
                # Pass the config to the factory. The factory can choose to use it or not.
                tool_instance = definition.custom_factory(config)
            
            # Fall back to instantiating the tool_class
            elif definition.tool_class:
                # For class-based tools, the convention is to pass the ToolConfig object
                # itself to the constructor under the 'config' keyword argument.
                logger.info(f"Creating tool instance for '{name}' using class '{definition.tool_class.__name__}' and passing ToolConfig.")
                tool_instance = definition.tool_class(config=config)
            
            else:
                # This case should be prevented by ToolDefinition's validation
                raise ValueError(f"ToolDefinition for '{name}' is invalid: missing both tool_class and custom_factory.")

            logger.debug(f"Successfully created tool instance for '{name}'")
            return tool_instance

        except Exception as e:
            creator_type = "factory" if definition.custom_factory else f"class '{definition.tool_class.__name__}'"
            logger.error(f"Failed to create tool instance for '{name}' using {creator_type}: {e}", exc_info=True)
            raise TypeError(f"Failed to create tool '{name}': {e}") from e

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
