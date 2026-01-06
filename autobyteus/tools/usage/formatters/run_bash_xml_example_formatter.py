# file: autobyteus/autobyteus/tools/usage/formatters/run_bash_xml_example_formatter.py
"""
XML Example formatter for the run_bash tool using shorthand <run_bash> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class RunBashXmlExampleFormatter(BaseExampleFormatter):
    """
    Formats usage examples for run_bash using the shorthand <run_bash> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates usage examples for run_bash.
        """
        return '''### Example 1: List files

<run_bash>
ls -la
</run_bash>

### Example 2: Run tests

<run_bash>
python -m pytest tests/ -v
</run_bash>'''
