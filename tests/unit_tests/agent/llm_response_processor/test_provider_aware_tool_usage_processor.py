# file: autobyteus/tests/unit_tests/agent/llm_response_processor/test_provider_aware_tool_usage_processor.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.llm_response_processor import ProviderAwareToolUsageProcessor
from autobyteus.agent.context import AgentContext, AgentConfig
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def mock_context_factory():
    def _factory(use_xml: bool, provider: LLMProvider):
        # Create mocks for the nested objects to accurately reflect the real structure
        mock_model = MagicMock(spec=LLMModel)
        mock_model.provider = provider

        mock_llm_instance = MagicMock(spec=BaseLLM)
        mock_llm_instance.model = mock_model

        mock_config = MagicMock(spec=AgentConfig)
        mock_config.use_xml_tool_format = use_xml
        
        # Create the main context mock and assign the nested mocks
        context = MagicMock(spec=AgentContext)
        context.agent_id = "test_agent_123"
        context.config = mock_config
        context.llm_instance = mock_llm_instance
        
        context.input_event_queues = AsyncMock()
        context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()
        return context
    return _factory

@pytest.mark.asyncio
@patch('autobyteus.agent.llm_response_processor.provider_aware_tool_usage_processor.XmlResponseProcessorProvider')
@patch('autobyteus.agent.llm_response_processor.provider_aware_tool_usage_processor.JsonResponseProcessorProvider')
async def test_delegates_to_xml_provider(mock_json_provider_cls, mock_xml_provider_cls, mock_context_factory):
    """
    Verify it uses the XML provider when context.config.use_xml_tool_format is True.
    """
    # Arrange
    master_processor = ProviderAwareToolUsageProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    
    mock_specific_processor = AsyncMock()
    mock_xml_provider_cls.return_value.get_processor.return_value = mock_specific_processor
    
    response = CompleteResponse(content="<tool_calls></tool_calls>")
    trigger_event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    await master_processor.process_response(response, mock_context, trigger_event)

    # Assert
    mock_xml_provider_cls.assert_called_once()
    # Verify the provider was correctly retrieved from the nested mock structure
    mock_xml_provider_cls.return_value.get_processor.assert_called_once_with(LLMProvider.ANTHROPIC)
    mock_json_provider_cls.assert_not_called()
    mock_specific_processor.process_response.assert_awaited_once_with(response, mock_context, trigger_event)


@pytest.mark.asyncio
@patch('autobyteus.agent.llm_response_processor.provider_aware_tool_usage_processor.XmlResponseProcessorProvider')
@patch('autobyteus.agent.llm_response_processor.provider_aware_tool_usage_processor.JsonResponseProcessorProvider')
async def test_delegates_to_json_provider(mock_json_provider_cls, mock_xml_provider_cls, mock_context_factory):
    """
    Verify it uses the JSON provider when context.config.use_xml_tool_format is False.
    """
    # Arrange
    master_processor = ProviderAwareToolUsageProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    
    mock_specific_processor = AsyncMock()
    mock_json_provider_cls.return_value.get_processor.return_value = mock_specific_processor
    
    response = CompleteResponse(content="{}")
    trigger_event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    await master_processor.process_response(response, mock_context, trigger_event)

    # Assert
    mock_json_provider_cls.assert_called_once()
    # Verify the provider was correctly retrieved from the nested mock structure
    mock_json_provider_cls.return_value.get_processor.assert_called_once_with(LLMProvider.OPENAI)
    mock_xml_provider_cls.assert_not_called()
    mock_specific_processor.process_response.assert_awaited_once_with(response, mock_context, trigger_event)
