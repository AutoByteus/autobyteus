
import pytest
import re
from unittest.mock import MagicMock

from autobyteus.tools.usage.formatters.write_file_xml_schema_formatter import WriteFileXmlSchemaFormatter
from autobyteus.tools.usage.formatters.write_file_xml_example_formatter import WriteFileXmlExampleFormatter
from autobyteus.tools.registry import ToolDefinition

class TestWriteFileXmlFormatter:
    
    @pytest.fixture
    def mock_tool_definition(self):
        tool_def = MagicMock(spec=ToolDefinition)
        tool_def.name = "write_file"
        tool_def.description = "Writes a file."
        return tool_def

    def test_schema_uses_standard_xml_structure(self, mock_tool_definition):
        formatter = WriteFileXmlSchemaFormatter()
        schema = formatter.provide(mock_tool_definition)
        
        # Verify it uses the standard <tool name="write_file"> syntax
        assert '<tool name="write_file">' in schema
        assert '</tool>' in schema
        assert '<arguments>' in schema
        
    def test_schema_includes_sentinel_instructions(self, mock_tool_definition):
        formatter = WriteFileXmlSchemaFormatter()
        schema = formatter.provide(mock_tool_definition)
        
        # Verify instructions for sentinels are present
        assert '__START_CONTENT__' in schema
        assert '__END_CONTENT__' in schema
        assert 'sentinel tags' in schema

    def test_example_uses_standard_xml_structure(self, mock_tool_definition):
        formatter = WriteFileXmlExampleFormatter()
        example = formatter.provide(mock_tool_definition)
        
        # Verify it uses the standard <tool name="write_file"> syntax
        assert '<tool name="write_file">' in example
        assert '</tool>' in example
        assert '<arguments>' in example

    def test_example_includes_sentinel_tags(self, mock_tool_definition):
        formatter = WriteFileXmlExampleFormatter()
        example = formatter.provide(mock_tool_definition)
        
        # Verify sentinels are used in the example content
        assert '__START_CONTENT__' in example
        assert '__END_CONTENT__' in example
        
        # Verify a specific example structure roughly matches expectations
        assert '<arg name="path">/path/to/hello.py</arg>' in example
