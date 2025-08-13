# file: autobyteus/autobyteus/tools/usage/registries/tool_formatter_pair.py
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.usage.formatters import BaseSchemaFormatter, BaseExampleFormatter

@dataclass(frozen=True)
class ToolFormatterPair:
    """
    A container that pairs a tool's schema formatter with its corresponding example formatter.
    This provides a complete set of formatters for a given provider's tool usage style.
    """
    schema_formatter: 'BaseSchemaFormatter'
    example_formatter: 'BaseExampleFormatter'
