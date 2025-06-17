# file: autobyteus/tests/unit_tests/tools/usage/providers/test_xml_tool_usage_parser_provider.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.tools.usage.providers import XmlToolUsageParserProvider

def test_provider_uses_xml_parser_registry():
    patch_target = 'autobyteus.tools.usage.providers.xml_tool_usage_parser_provider.XmlToolUsageParserRegistry'
    with patch(patch_target) as MockRegistry:
        mock_registry_instance = MockRegistry.return_value
        mock_parser = MagicMock()
        mock_registry_instance.get_parser.return_value = mock_parser

        provider = XmlToolUsageParserProvider()
        result = provider.provide()

        assert result is mock_parser
        MockRegistry.assert_called_once()
        mock_registry_instance.get_parser.assert_called_once()
