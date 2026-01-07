# file: autobyteus/autobyteus/tools/usage/formatters/patch_file_xml_schema_formatter.py
"""
XML Schema formatter for the patch_file tool using standard <tool name="patch_file"> syntax.
"""
from typing import TYPE_CHECKING

from .base_formatter import BaseSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition


class PatchFileXmlSchemaFormatter(BaseSchemaFormatter):
    """
    Formats the patch_file tool schema using the standard <tool name="patch_file"> XML syntax.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates the schema description for patch_file using standard XML syntax
        with specific instructions for sentinel tags to support robust streaming.
        """
        return '''<tool name="patch_file">
    <arguments>
        <arg name="path" type="string" description="The absolute or relative path to the file to patch." required="true" />
        <arg name="patch" type="string" description="The unified diff patch to apply to the file." required="true">
            IMPORTANT: To ensure reliable streaming, you MUST enclose the patch content with the sentinel tags __START_PATCH__ and __END_PATCH__.
            The parser will strip these tags, but they are critical for preventing XML parsing errors if the patch contains special characters.
        </arg>
    </arguments>
</tool>'''
