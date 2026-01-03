# file: autobyteus/autobyteus/tools/usage/formatters/run_terminal_cmd_xml_schema_formatter.py
"""
XML Schema formatter for the run_terminal_cmd tool using shorthand <run_terminal_cmd> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class RunTerminalCmdXmlSchemaFormatter(BaseSchemaFormatter):
    """
    Formats the run_terminal_cmd tool schema using the shorthand <run_terminal_cmd> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates the schema description for run_terminal_cmd using shorthand syntax.
        """
        return '''## run_terminal_cmd

Runs a command in the terminal.

**Syntax:**
```xml
<run_terminal_cmd>
command_to_execute
</run_terminal_cmd>
```

**Parameters:**
- Content between tags: The shell command to execute.

The command runs in the agent's configured working directory.'''
