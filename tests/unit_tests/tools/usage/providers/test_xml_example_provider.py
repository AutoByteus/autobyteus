# file: autobyteus/tests/unit_tests/tools/usage/providers/test_xml_example_provider.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.tools.usage.providers.xml_example_provider import XmlExampleProvider
from autobyteus.tools.registry import ToolDefinition

@pytest.fixture
def mock_tool_def():
    return MagicMock(spec=ToolDefinition)

def test_provider_uses_xml_example_registry(mock_tool_def: MagicMock):
    """
    Tests that the provider correctly uses the XmlExampleFormatterRegistry.
    """
    # CORRECTED: Patch the Registry, not the Formatter.
    patch_target = 'autobyteus.tools.usage.providers.xml_example_provider.XmlExampleFormatterRegistry'
    with patch(patch_target) as MockRegistry:
        mock_registry_instance = MockRegistry.return_value
        mock_formatter = MagicMock()
        mock_formatter.provide.return_value = "<tool_call>mocked_xml_example</tool_call>"
        mock_registry_instance.get_formatter.return_value = mock_formatter

        provider = XmlExampleProvider()
        result = provider.provide(mock_tool_def)

        assert result == "<tool_call>mocked_xml_example</tool_call>"
        MockRegistry.assert_called_once()
        mock_registry_instance.get_formatter.assert_called_once()
        mock_formatter.provide.assert_called_once_with(mock_tool_def)
