# file: autobyteus/tests/unit_tests/agent/llm_response_processor/providers/test_json_response_processor_provider.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.llm.providers import LLMProvider
from autobyteus.agent.llm_response_processor.providers import JsonResponseProcessorProvider

@patch('autobyteus.agent.llm_response_processor.providers.json_response_processor_provider.JsonResponseProcessorRegistry')
def test_json_response_processor_provider(mock_registry_class):
    """
    Tests that the JsonResponseProcessorProvider correctly uses its registry.
    """
    # Arrange
    mock_registry_instance = mock_registry_class.return_value
    mock_processor = MagicMock()
    mock_registry_instance.get_processor.return_value = mock_processor
    
    provider = JsonResponseProcessorProvider()
    
    # Act
    result = provider.get_processor(LLMProvider.OPENAI)
    
    # Assert
    mock_registry_class.assert_called_once()
    mock_registry_instance.get_processor.assert_called_once_with(LLMProvider.OPENAI)
    assert result is mock_processor
