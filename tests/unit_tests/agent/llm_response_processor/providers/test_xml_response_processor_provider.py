# file: autobyteus/tests/unit_tests/agent/llm_response_processor/providers/test_xml_response_processor_provider.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.llm.providers import LLMProvider
from autobyteus.agent.llm_response_processor.providers import XmlResponseProcessorProvider

@patch('autobyteus.agent.llm_response_processor.providers.xml_response_processor_provider.XmlResponseProcessorRegistry')
def test_xml_response_processor_provider(mock_registry_class):
    """
    Tests that the XmlResponseProcessorProvider correctly uses its registry.
    """
    # Arrange
    mock_registry_instance = mock_registry_class.return_value
    mock_processor = MagicMock()
    mock_registry_instance.get_processor.return_value = mock_processor
    
    provider = XmlResponseProcessorProvider()
    
    # Act
    result = provider.get_processor(LLMProvider.ANTHROPIC)
    
    # Assert
    mock_registry_class.assert_called_once()
    mock_registry_instance.get_processor.assert_called_once_with(LLMProvider.ANTHROPIC)
    assert result is mock_processor
