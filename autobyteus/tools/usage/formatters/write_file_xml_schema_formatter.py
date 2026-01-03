# file: autobyteus/autobyteus/tools/usage/formatters/write_file_xml_schema_formatter.py
"""
XML Schema formatter for the write_file tool using shorthand <write_file> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class WriteFileXmlSchemaFormatter(BaseSchemaFormatter):
    """
    Formats the write_file tool schema using the shorthand <write_file> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates the schema description for write_file using shorthand syntax.
        """
        return '''## write_file

Creates or overwrites a file with specified content.

**Syntax:**
```xml
<write_file path="file_path">
file_content
</write_file>
```

**Parameters:**
- `path` (required): The absolute or relative path where the file will be written.
- Content between tags: The string content to write to the file.

Creates parent directories if they don't exist.'''
