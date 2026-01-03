# file: autobyteus/autobyteus/tools/usage/formatters/write_file_xml_example_formatter.py
"""
XML Example formatter for the write_file tool using shorthand <write_file> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class WriteFileXmlExampleFormatter(BaseExampleFormatter):
    """
    Formats usage examples for write_file using the shorthand <write_file> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates usage examples for write_file.
        """
        return '''### Example 1: Create a Python file

<write_file path="/path/to/hello.py">
def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
</write_file>

### Example 2: Create a configuration file

<write_file path="config/settings.json">
{
    "debug": true,
    "log_level": "INFO"
}
</write_file>'''
