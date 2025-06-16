# file: autobyteus/tests/unit_tests/tools/usage/providers/test_xml_schema_provider.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.tools.usage.providers.xml_schema_provider import XmlSchemaProvider
from autobyteus.tools.registry import ToolDefinition
from autobyteus.llm.providers import LLMProvider

@pytest.fixture
def mock_tool_def():
    return MagicMock(spec=ToolDefinition)

def test_provider_uses_xml_registry(mock_tool_def: MagicMock):
    """
    Tests that the provider correctly uses the XmlSchemaFormatterRegistry.
    """
    # CORRECTED: Patch the Registry, not the Formatter.
    patch_target = 'autobyteus.tools.usage.providers.xml_schema_provider.XmlSchemaFormatterRegistry'
    with patch(patch_target) as MockRegistry:
        mock_registry_instance = MockRegistry.return_value
        mock_formatter = MagicMock()
        mock_formatter.provide.return_value = "<tool>mocked_xml_from_registry</tool>"
        mock_registry_instance.get_formatter.return_value = mock_formatter

        # Instantiate the provider *inside* the patch context
        provider = XmlSchemaProvider()
        result = provider.provide(mock_tool_def, llm_provider=LLMProvider.OPENAI)

        assert result == "<tool>mocked_xml_from_registry</tool>"
        MockRegistry.assert_called_once()
        mock_registry_instance.get_formatter.assert_called_once_with(LLMProvider.OPENAI)
        mock_formatter.provide.assert_called_once_with(mock_tool_def)
