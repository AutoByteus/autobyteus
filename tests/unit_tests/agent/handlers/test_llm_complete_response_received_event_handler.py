import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

from autobyteus.agent.handlers.llm_complete_response_received_event_handler import LLMCompleteResponseReceivedEventHandler
from autobyteus.agent.events.agent_events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.agent.llm_response_processor.base_processor import BaseLLMResponseProcessor
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.agent.tool_invocation import ToolInvocation


# Mock LLM Response Processor
class MockLLMResponseProcessor(BaseLLMResponseProcessor):
    _should_handle = False
    _processed_text = None

    def get_name(self) -> str:
        return "mock_processor"

    async def process_response(self, response: CompleteResponse, context, triggering_event) -> bool:
        self._processed_text = response.content
        if self._should_handle:
            mock_ti = MagicMock(spec=ToolInvocation)
            mock_ti.id = "test-tool-id"
            mock_ti.name = "processed_tool"
            await context.input_event_queues.enqueue_tool_invocation_request(
                PendingToolInvocationEvent(tool_invocation=mock_ti)
            )
            return True
        return False

    def reset(self):
        self._should_handle = False
        self._processed_text = None


@pytest.fixture
def mock_processor_instance():
    # Use an instance of the mock processor for tests
    processor = MockLLMResponseProcessor()
    processor.reset()
    return processor

@pytest.fixture
def llm_complete_handler(agent_context, mock_processor_instance):
    # Set the processor instance on the agent's config
    agent_context.config.llm_response_processors = [mock_processor_instance]
    
    # Ensure notifier is mocked on status_manager
    if not hasattr(agent_context.status_manager, 'notifier') or not isinstance(agent_context.status_manager.notifier, AsyncMock):
        agent_context.status_manager.notifier = AsyncMock()
        
    handler = LLMCompleteResponseReceivedEventHandler()
    return handler


@pytest.mark.asyncio
async def test_handle_response_processed_by_processor(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, mock_processor_instance, caplog):
    """Test when an LLMResponseProcessor handles the response."""
    response_text = "LLM response with tool call <tool>..."
    mock_usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    complete_response = CompleteResponse(content=response_text, usage=mock_usage)
    event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)

    mock_processor_instance._should_handle = True

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    log_msg = (
        f"Agent '{agent_context.agent_id}' handling LLMCompleteResponseReceivedEvent. "
        f"Response Length: {len(response_text)}, Reasoning Length: 0, IsErrorFlagged: False, "
        f"TokenUsage: {mock_usage}"
    )
    assert log_msg in caplog.text
    assert f"LLMResponseProcessor '{mock_processor_instance.get_name()}' handled the response" in caplog.text
    assert mock_processor_instance._processed_text == response_text
    
    agent_context.status_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()
    
    agent_context.input_event_queues.enqueue_tool_invocation_request.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert isinstance(enqueued_event, PendingToolInvocationEvent)
    assert enqueued_event.tool_invocation.name == "processed_tool"


@pytest.mark.asyncio
async def test_handle_response_not_processed(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, mock_processor_instance, caplog):
    """Test when no LLMResponseProcessor handles the response."""
    response_text = "Final LLM answer, no tools."
    complete_response = CompleteResponse(content=response_text, usage=None)
    event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    
    mock_processor_instance._should_handle = False

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    assert "No LLMResponseProcessor handled the response" in caplog.text
    assert "Emitting the full LLM response as a final answer and completion signal" in caplog.text
    
    assert mock_processor_instance._processed_text == response_text
    
    agent_context.status_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once_with(complete_response)


@pytest.mark.asyncio
async def test_handle_error_response_event(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, mock_processor_instance, caplog):
    """Test when the event itself indicates an error response."""
    error_text = "An error occurred in a previous stage."
    complete_response = CompleteResponse(content=error_text, usage=None)
    event = LLMCompleteResponseReceivedEvent(complete_response=complete_response, is_error=True)
    
    mock_processor_instance._should_handle = False

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    assert "LLMCompleteResponseReceivedEvent was marked as an error response" in caplog.text
    assert "Skipping LLMResponseProcessor attempts" in caplog.text
    
    assert mock_processor_instance._processed_text is None
    
    agent_context.status_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once_with(complete_response)


@pytest.mark.asyncio
async def test_handle_no_processors_configured(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test behavior when config has no llm_response_processors."""
    response_text = "Response when no processors are configured."
    complete_response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    
    agent_context.config.llm_response_processors = []

    with caplog.at_level(logging.DEBUG):
        await llm_complete_handler.handle(event, agent_context)

    assert "No LLM response processors configured" in caplog.text
    
    agent_context.status_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()


@pytest.mark.asyncio
async def test_handle_invalid_processor_type_in_config(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test that a non-processor object in the config list is skipped."""
    response_text = "Response with invalid processor."
    complete_response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    
    class NotAProcessor:
        pass

    agent_context.config.llm_response_processors = [NotAProcessor()]

    with caplog.at_level(logging.ERROR):
        await llm_complete_handler.handle(event, agent_context)
    
    assert "Invalid LLM response processor type in config" in caplog.text
    agent_context.status_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()


@pytest.mark.asyncio
async def test_handle_processor_raises_exception(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, mock_processor_instance, caplog):
    """Test behavior when a processor's method raises an exception."""
    response_text = "Response that causes processor error."
    complete_response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
        
    async def mock_process_response_error(response, context, triggering_event):
        raise ValueError("Simulated processor error")

    # Patch the instance's method
    mock_processor_instance.process_response = mock_process_response_error

    with caplog.at_level(logging.ERROR):
        await llm_complete_handler.handle(event, agent_context)

    assert f"Error while using LLMResponseProcessor '{mock_processor_instance.get_name()}': Simulated processor error" in caplog.text
    
    # It should still emit the original response as final output
    agent_context.status_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()
    
    # And it should notify about the error during output generation
    agent_context.status_manager.notifier.notify_agent_error_output_generation.assert_called_once_with(
        error_source=f"LLMResponseProcessor.{mock_processor_instance.get_name()}",
        error_message="Simulated processor error"
    )

def test_llm_complete_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = LLMCompleteResponseReceivedEventHandler()
    assert "LLMCompleteResponseReceivedEventHandler initialized." in caplog.text
