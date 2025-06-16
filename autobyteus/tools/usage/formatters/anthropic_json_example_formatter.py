# file: autobyteus/autobyteus/tools/usage/formatters/anthropic_json_example_formatter.py
from typing import TYPE_CHECKING

from .base_formatter import BaseExampleFormatter
from .default_xml_example_formatter import DefaultXmlExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class AnthropicJsonExampleFormatter(BaseExampleFormatter):
    """
    Formats a tool usage example for Anthropic models. Since Anthropic uses XML
    for tool calls, this formatter returns a string representing the XML call.
    """
    def provide(self, tool_definition: 'ToolDefinition') -> str:
        # Anthropic expects XML tool call examples.
        # We use the XML formatter's logic directly.
        return DefaultXmlExampleFormatter().provide(tool_definition)
