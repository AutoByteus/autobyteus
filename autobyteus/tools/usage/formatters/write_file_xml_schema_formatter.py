# file: autobyteus/autobyteus/tools/usage/formatters/write_file_xml_schema_formatter.py
"""
XML Schema formatter for the write_file tool using shorthand <write_file> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseXmlSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class WriteFileXmlSchemaFormatter(BaseXmlSchemaFormatter):
    """
    Formats the write_file tool schema using the shorthand <write_file> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates the schema description for write_file using standard XML syntax
        but with specific instructions for sentinel tags to support robust streaming.
        """
        return '''<tool name="write_file">
    <arguments>
        <arg name="path" type="string" description="The absolute or relative path where the file will be written." required="true" />
        <arg name="content" type="string" description="The content to write to the file." required="true">
            IMPORTANT: To ensure reliable streaming, you MUST enclose the file content with the sentinel tags __START_CONTENT__ and __END_CONTENT__.
            The parser will strip these tags, but they are critical for preventing XML parsing errors if the content contains special characters.
        </arg>
    </arguments>
</tool>'''
