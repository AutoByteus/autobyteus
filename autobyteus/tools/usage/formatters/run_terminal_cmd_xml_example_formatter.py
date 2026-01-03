# file: autobyteus/autobyteus/tools/usage/formatters/run_terminal_cmd_xml_example_formatter.py
"""
XML Example formatter for the run_terminal_cmd tool using shorthand <run_terminal_cmd> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class RunTerminalCmdXmlExampleFormatter(BaseExampleFormatter):
    """
    Formats usage examples for run_terminal_cmd using the shorthand <run_terminal_cmd> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates usage examples for run_terminal_cmd.
        """
        return '''### Example 1: List files

<run_terminal_cmd>
ls -la
</run_terminal_cmd>

### Example 2: Run tests

<run_terminal_cmd>
python -m pytest tests/ -v
</run_terminal_cmd>'''
