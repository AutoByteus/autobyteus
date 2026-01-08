# file: autobyteus/autobyteus/tools/usage/formatters/run_bash_xml_schema_formatter.py
"""
XML Schema formatter for the run_bash tool using shorthand <run_bash> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseXmlSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class RunBashXmlSchemaFormatter(BaseXmlSchemaFormatter):
    """
    Formats the run_bash tool schema using the shorthand <run_bash> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates the schema description for run_bash using shorthand syntax.
        """
        return '''## run_bash

Runs a command in the terminal.

**Syntax:**
```xml
<run_bash>
command_to_execute
</run_bash>
```

**Parameters:**
- Content between tags: The shell command to execute.

The command runs in the agent's configured working directory.'''
