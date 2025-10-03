# file: autobyteus/autobyteus/tools/registry/tool_definition.py
import logging
import json
from typing import Dict, Any, List as TypingList, Type, TYPE_CHECKING, Optional, Callable

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.tools.tool_origin import ToolOrigin
# Import default formatters directly to provide convenience methods
from autobyteus.tools.usage.formatters import (
    DefaultXmlSchemaFormatter,
    DefaultJsonSchemaFormatter,
    DefaultXmlExampleFormatter,
    DefaultJsonExampleFormatter
)

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolDefinition:
    """
    Represents the definition of a tool, containing its metadata and the means
    to create an instance. It can generate provider-agnostic usage information on demand.
    """
    def __init__(self,
                 name: str,
                 description: str,
                 argument_schema: Optional['ParameterSchema'],
                 origin: ToolOrigin,
                 category: str,
                 config_schema: Optional['ParameterSchema'] = None,
                 tool_class: Optional[Type['BaseTool']] = None,
                 custom_factory: Optional[Callable[['ToolConfig'], 'BaseTool']] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initializes the ToolDefinition.
        """
        if not name or not isinstance(name, str):
            raise ValueError("ToolDefinition requires a non-empty string 'name'.")
        if not description or not isinstance(description, str):
            raise ValueError(f"ToolDefinition '{name}' requires a non-empty string 'description'.")

        if tool_class is None and custom_factory is None:
            raise ValueError(f"ToolDefinition '{name}' must provide either a 'tool_class' or a 'custom_factory'.")
        if tool_class is not None and custom_factory is not None:
            raise ValueError(f"ToolDefinition '{name}' cannot have both a 'tool_class' and a 'custom_factory'.")
        
        if tool_class and not isinstance(tool_class, type):
            raise TypeError(f"ToolDefinition '{name}' requires a valid class for 'tool_class'.")
        if custom_factory and not callable(custom_factory):
            raise TypeError(f"ToolDefinition '{name}' requires a callable for 'custom_factory'.")

        if argument_schema is not None and not isinstance(argument_schema, ParameterSchema):
             raise TypeError(f"ToolDefinition '{name}' received an invalid 'argument_schema'. Expected ParameterSchema or None.")
        if config_schema is not None and not isinstance(config_schema, ParameterSchema):
             raise TypeError(f"ToolDefinition '{name}' received an invalid 'config_schema'. Expected ParameterSchema or None.")
        if not isinstance(origin, ToolOrigin):
            raise TypeError(f"ToolDefinition '{name}' requires a ToolOrigin for 'origin'. Got {type(origin)}")
        
        # Validation for MCP-specific metadata
        if origin == ToolOrigin.MCP and not (metadata and metadata.get("mcp_server_id")):
            raise ValueError(f"ToolDefinition '{name}' with origin MCP must provide a 'mcp_server_id' in its metadata.")

        self._name = name
        self._description = description
        self._argument_schema: Optional['ParameterSchema'] = argument_schema
        self._config_schema: Optional['ParameterSchema'] = config_schema
        self._tool_class = tool_class
        self._custom_factory = custom_factory
        self._origin = origin
        self._category = category
        self._metadata = metadata or {}
        
        logger.debug(f"ToolDefinition created for tool '{self.name}'.")

    # --- Properties ---
    @property
    def name(self) -> str: return self._name
    @property
    def description(self) -> str: return self._description
    @property
    def tool_class(self) -> Optional[Type['BaseTool']]: return self._tool_class
    @property
    def custom_factory(self) -> Optional[Callable[['ToolConfig'], 'BaseTool']]: return self._custom_factory
    @property
    def argument_schema(self) -> Optional['ParameterSchema']: return self._argument_schema
    @property
    def config_schema(self) -> Optional['ParameterSchema']: return self._config_schema
    @property
    def origin(self) -> ToolOrigin: return self._origin
    @property
    def category(self) -> str: return self._category
    @property
    def metadata(self) -> Dict[str, Any]: return self._metadata
    
    # --- Convenience Schema/Example Generation API (using default formatters) ---
    def get_usage_xml(self, provider: Optional[LLMProvider] = None) -> str:
        """
        Generates the default XML usage schema string for this tool.
        The provider argument is ignored, kept for API consistency.
        """
        formatter = DefaultXmlSchemaFormatter()
        return formatter.provide(self)

    def get_usage_json(self, provider: Optional[LLMProvider] = None) -> Dict[str, Any]:
        """
        Generates the default JSON usage schema as a dictionary.
        The provider argument is ignored, kept for API consistency.
        """
        formatter = DefaultJsonSchemaFormatter()
        return formatter.provide(self)

    def get_usage_xml_example(self, provider: Optional[LLMProvider] = None) -> str:
        """
        Generates a default XML usage example string for this tool.
        The provider argument is ignored, kept for API consistency.
        """
        formatter = DefaultXmlExampleFormatter()
        return formatter.provide(self)

    def get_usage_json_example(self, provider: Optional[LLMProvider] = None) -> Any:
        """
        Generates a default JSON usage example as a dictionary.
        The provider argument is ignored, kept for API consistency.
        """
        formatter = DefaultJsonExampleFormatter()
        return formatter.provide(self)

    # --- Other methods ---
    @property
    def has_instantiation_config(self) -> bool:
        return self._config_schema is not None and len(self._config_schema) > 0

    def validate_instantiation_config(self, config_data: Dict[str, Any]) -> tuple[bool, TypingList[str]]:
        if not self._config_schema:
            if config_data:
                return False, [f"Tool '{self.name}' does not accept instantiation configuration parameters"]
            return True, []
        return self._config_schema.validate_config(config_data)

    def __repr__(self) -> str:
        creator_repr = f"class='{self._tool_class.__name__}'" if self._tool_class else "factory=True"
        metadata_repr = f", metadata={self.metadata}" if self.metadata else ""
        return (f"ToolDefinition(name='{self.name}', origin='{self.origin.value}', category='{self.category}'{metadata_repr}, {creator_repr})")
