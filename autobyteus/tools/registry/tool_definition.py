# file: autobyteus/tools/registry/tool_definition.py
import logging
from typing import Dict, Any, List, Type, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.tools.tool_config_schema import ToolConfigSchema

logger = logging.getLogger(__name__)

class ToolDefinition:
    """
    Represents the definition of a tool, containing its name, description,
    tool class reference, and optional configuration schema.
    """
    def __init__(self,
                 name: str,
                 description: str,
                 tool_class: Type['BaseTool'],
                 config_schema: Optional['ToolConfigSchema'] = None):
        """
        Initializes the ToolDefinition.

        Args:
            name: The unique name/identifier of the tool.
            description: The static usage description string for the tool (e.g., XML usage format).
            tool_class: The class reference of the tool for instantiation.
            config_schema: Optional schema describing the tool's configuration parameters.

        Raises:
            ValueError: If name or description are empty or invalid.
            TypeError: If tool_class is not a valid class.
        """
        if not name or not isinstance(name, str):
            raise ValueError("ToolDefinition requires a non-empty string 'name'.")
        if not description or not isinstance(description, str):
            raise ValueError(f"ToolDefinition '{name}' requires a non-empty string 'description'.")
        if not isinstance(tool_class, type):
            raise TypeError(f"ToolDefinition '{name}' requires a valid class for 'tool_class'.")

        self._name = name
        self._description = description
        self._tool_class = tool_class
        self._config_schema = config_schema

        schema_info = f"with config schema ({len(config_schema)} parameters)" if config_schema else "without config schema"
        logger.debug(f"ToolDefinition created for tool '{self.name}' with class '{self.tool_class.__name__}' {schema_info}.")

    @property
    def name(self) -> str:
        """The unique name/identifier of the tool."""
        return self._name

    @property
    def description(self) -> str:
        """The static usage description string for the tool."""
        return self._description

    @property
    def tool_class(self) -> Type['BaseTool']:
        """The class reference of the tool."""
        return self._tool_class

    @property
    def config_schema(self) -> Optional['ToolConfigSchema']:
        """The configuration schema for the tool, if any."""
        return self._config_schema

    @property
    def has_config(self) -> bool:
        """Whether this tool has configurable parameters."""
        return self._config_schema is not None and len(self._config_schema) > 0

    def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate configuration data against this tool's schema.
        
        Args:
            config_data: Configuration dictionary to validate.
            
        Returns:
            tuple: (is_valid, list_of_error_messages)
        """
        if not self._config_schema:
            # No schema means no configuration expected
            if config_data:
                return False, [f"Tool '{self.name}' does not accept configuration parameters"]
            return True, []
        
        return self._config_schema.validate_config(config_data)

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values for this tool."""
        if not self._config_schema:
            return {}
        return self._config_schema.get_defaults()

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        desc_repr = self.description
        if len(desc_repr) > 70:
             desc_repr = desc_repr[:67] + "..."
        # Remove newlines/tabs from repr for cleaner logging if description is multiline XML
        desc_repr = desc_repr.replace('\n', '\\n').replace('\t', '\\t')
        
        config_repr = f", config_params={len(self._config_schema)}" if self._config_schema else ", no_config"
        
        return (f"ToolDefinition(name='{self.name}', class='{self.tool_class.__name__}'{config_repr}, "
                f"description='{desc_repr}')")

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dictionary representation of the tool definition."""
        result = {
            "name": self.name,
            "description": self.description,
            "tool_class": self.tool_class.__name__,
            "has_config": self.has_config,
        }
        
        if self._config_schema:
            result["config_schema"] = self._config_schema.to_dict()
        
        return result
