# file: autobyteus/tools/registry/tool_definition.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ToolDefinition:
    """
    Represents the simplified static definition of a tool, containing
    only its name and usage description string.
    """
    def __init__(self,
                 name: str,
                 description: str):
        """
        Initializes the ToolDefinition.

        Args:
            name: The unique name/identifier of the tool.
            description: The static usage description string for the tool (e.g., XML usage format).

        Raises:
            ValueError: If name or description are empty or invalid.
        """
        if not name or not isinstance(name, str):
            raise ValueError("ToolDefinition requires a non-empty string 'name'.")
        if not description or not isinstance(description, str):
            raise ValueError(f"ToolDefinition '{name}' requires a non-empty string 'description'.")

        self._name = name
        self._description = description

        logger.debug(f"ToolDefinition created for tool '{self.name}'.")

    @property
    def name(self) -> str:
        """The unique name/identifier of the tool."""
        return self._name

    @property
    def description(self) -> str:
        """The static usage description string for the tool."""
        return self._description

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        desc_repr = self.description
        if len(desc_repr) > 70:
             desc_repr = desc_repr[:67] + "..."
        # Remove newlines/tabs from repr for cleaner logging if description is multiline XML
        desc_repr = desc_repr.replace('\n', '\\n').replace('\t', '\\t')
        return (f"ToolDefinition(name='{self.name}', description='{desc_repr}')")

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dictionary representation of the tool definition."""
        return {
            "name": self.name,
            "description": self.description,
        }

