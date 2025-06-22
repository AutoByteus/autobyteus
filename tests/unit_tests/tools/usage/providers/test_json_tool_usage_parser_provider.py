# file: autobyteus/tests/unit_tests/tools/usage/providers/test_json_tool_usage_parser_provider.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.tools.usage.providers import JsonToolUsageParserProvider
from autobyteus.llm.providers import LLMProvider

def test_provider_uses_registry_with_provider():
    patch_target = 'autobyteus.tools.usage.providers.json_tool_usage_parser_provider.JsonToolUsageParserRegistry'
    with patch(patch_target) as MockRegistry:
        mock_registry_instance = MockRegistry.return_value
        mock_parser = MagicMock()
        mock_registry_instance.get_parser.return_value = mock_parser

        provider = JsonToolUsageParserProvider()
        result = provider.provide(llm_provider=LLMProvider.GEMINI)

        assert result is mock_parser
        MockRegistry.assert_called_once()
        mock_registry_instance.get_parser.assert_called_once_with(LLMProvider.GEMINI)

def test_provider_uses_registry_default():
    patch_target = 'autobyteus.tools.usage.providers.json_tool_usage_parser_provider.JsonToolUsageParserRegistry'
    with patch(patch_target) as MockRegistry:
        mock_registry_instance = MockRegistry.return_value
        mock_parser = MagicMock()
        mock_registry_instance.get_default_parser.return_value = mock_parser

        provider = JsonToolUsageParserProvider()
        result = provider.provide(llm_provider=None)

        assert result is mock_parser
        MockRegistry.assert_called_once()
        mock_registry_instance.get_default_parser.assert_called_once()
