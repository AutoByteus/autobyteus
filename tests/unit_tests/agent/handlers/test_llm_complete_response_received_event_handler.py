import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

from autobyteus.agent.handlers.llm_complete_response_received_event_handler import LLMCompleteResponseReceivedEventHandler
from autobyteus.agent.events.agent_events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.agent.events.agent_event_queues import END_OF_STREAM_SENTINEL
from autobyteus.agent.llm_response_processor.base_processor import BaseLLMResponseProcessor
from autobyteus.agent.llm_response_processor.processor_registry import LLMResponseProcessorRegistry, LLMResponseProcessorDefinition


# Mock LLM Response Processor
class MockLLMResponseProcessor(BaseLLMResponseProcessor):
    _should_handle = False
    _processed_text = None
    _enqueued_event = None

    @classmethod
    def get_name(cls) -> str:
        return "mock_processor"

    async def process_response(self, response: str, context) -> bool:
        MockLLMResponseProcessor._processed_text = response
        if MockLLMResponseProcessor._should_handle:
            # Simulate enqueuing an event if handled
            # For simplicity, just store it. A real processor would enqueue.
            MockLLMResponseProcessor._enqueued_event = PendingToolInvocationEvent(tool_invocation=MagicMock())
            # In a real scenario, it would be:
            # await context.queues.enqueue_tool_invocation_request(MockLLMResponseProcessor._enqueued_event)
            return True
        return False

    @classmethod
    def reset(cls):
        cls._should_handle = False
        cls._processed_text = None
        cls._enqueued_event = None


@pytest.fixture
def llm_complete_handler(agent_context): # Depends on agent_context for definition
    # Setup a mock processor in the registry for testing
    registry = LLMResponseProcessorRegistry() # Use a fresh registry for this test if needed
    
    # Clear if it's a singleton and might have other things
    if hasattr(LLMResponseProcessorRegistry, 'instance'):
        LLMResponseProcessorRegistry.instance = None # type: ignore
        registry = LLMResponseProcessorRegistry()


    MockLLMResponseProcessor.reset() # Reset its state
    mock_processor_def = LLMResponseProcessorDefinition(
        name="mock_processor",
        processor_class=MockLLMResponseProcessor # type: ignore
    )
    registry.register_processor(mock_processor_def)
    
    handler = LLMCompleteResponseReceivedEventHandler()
    handler.llm_response_processor_registry = registry # Inject our test registry

    # Configure agent_context to use this processor
    agent_context.definition.llm_response_processor_names = ["mock_processor"]
    return handler


@pytest.mark.asyncio
async def test_handle_response_processed_by_processor(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test when an LLMResponseProcessor handles the response."""
    response_text = "LLM response with tool call <tool>..."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)

    MockLLMResponseProcessor._should_handle = True # Configure mock processor to handle

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling LLMCompleteResponseReceivedEvent." in caplog.text
    assert f"Agent '{agent_context.agent_id}': LLMResponseProcessor 'mock_processor' handled the response" in caplog.text
    
    # Ensure the processor was called with the correct response
    assert MockLLMResponseProcessor._processed_text == response_text
    
    # Ensure final message queue was NOT used because processor handled it
    agent_context.queues.assistant_final_message_queue.put.assert_not_called()
    
    # If the mock processor was to enqueue, we would check that here.
    # For this test, we confirm that MockLLMResponseProcessor._enqueued_event is set
    assert MockLLMResponseProcessor._enqueued_event is not None
    assert isinstance(MockLLMResponseProcessor._enqueued_event, PendingToolInvocationEvent)


@pytest.mark.asyncio
async def test_handle_response_not_processed_by_any_processor(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test when no LLMResponseProcessor handles the response."""
    response_text = "Final LLM answer, no tools."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)

    MockLLMResponseProcessor._should_handle = False # Processor will not handle

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling LLMCompleteResponseReceivedEvent." in caplog.text
    assert "No LLMResponseProcessor handled the response." in caplog.text
    assert f"Publishing the current LLM response as a final message" in caplog.text
    
    # Ensure processor was called
    assert MockLLMResponseProcessor._processed_text == response_text
    
    # Ensure final message queue received the response and sentinel
    agent_context.queues.assistant_final_message_queue.put.assert_any_call(response_text)
    agent_context.queues.assistant_final_message_queue.put.assert_any_call(END_OF_STREAM_SENTINEL)


@pytest.mark.asyncio
async def test_handle_error_response_event(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test when the event itself indicates an error response."""
    error_text = "An error occurred in a previous stage."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=error_text, is_error=True)

    MockLLMResponseProcessor._should_handle = False # Irrelevant as error path skips processors

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling LLMCompleteResponseReceivedEvent." in caplog.text
    assert "LLMCompleteResponseReceivedEvent was marked as an error response." in caplog.text
    assert "Skipping LLMResponseProcessor attempts." in caplog.text
    assert f"publishing a received error message to the assistant_final_message_queue" in caplog.text

    # Ensure processor was NOT called
    assert MockLLMResponseProcessor._processed_text is None 
    
    # Ensure final message queue received the error text and sentinel
    agent_context.queues.assistant_final_message_queue.put.assert_any_call(error_text)
    agent_context.queues.assistant_final_message_queue.put.assert_any_call(END_OF_STREAM_SENTINEL)


@pytest.mark.asyncio
async def test_handle_no_processors_configured(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test behavior when agent_definition has no llm_response_processor_names."""
    response_text = "Response when no processors are configured."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)
    
    agent_context.definition.llm_response_processor_names = [] # No processors configured

    MockLLMResponseProcessor._should_handle = False # Irrelevant

    with caplog.at_level(logging.DEBUG): # To see the debug log about no processors
        await llm_complete_handler.handle(event, agent_context)

    assert "No llm_response_processor_names configured in agent definition." in caplog.text
    assert "Publishing the current LLM response as a final message" in caplog.text

    # Ensure processor was NOT called
    assert MockLLMResponseProcessor._processed_text is None
    
    # Ensure final message queue received the response and sentinel
    agent_context.queues.assistant_final_message_queue.put.assert_any_call(response_text)
    agent_context.queues.assistant_final_message_queue.put.assert_any_call(END_OF_STREAM_SENTINEL)


@pytest.mark.asyncio
async def test_handle_processor_not_in_registry(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test behavior when a configured processor name is not in the registry."""
    response_text = "Response with unknown processor."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)
    
    agent_context.definition.llm_response_processor_names = ["unknown_processor", "mock_processor"]
    MockLLMResponseProcessor._should_handle = False # mock_processor won't handle

    with caplog.at_level(logging.WARNING): # To see warning about unknown processor
        await llm_complete_handler.handle(event, agent_context)

    assert "LLMResponseProcessor name 'unknown_processor' defined in agent_definition not found in registry." in caplog.text
    # mock_processor should still be tried and log that it didn't handle
    assert "LLMResponseProcessor 'mock_processor' did not handle the response." in caplog.text
    assert "Publishing the current LLM response as a final message" in caplog.text # Since no processor handled

    agent_context.queues.assistant_final_message_queue.put.assert_any_call(response_text)
    agent_context.queues.assistant_final_message_queue.put.assert_any_call(END_OF_STREAM_SENTINEL)


@pytest.mark.asyncio
async def test_handle_processor_raises_exception(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test behavior when a processor's process_response method raises an exception."""
    response_text = "Response that causes processor error."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)
    
    agent_context.definition.llm_response_processor_names = ["mock_processor"]
    
    async def mock_process_response_error(self, response, context):
        raise ValueError("Simulated processor error")

    original_process_response = MockLLMResponseProcessor.process_response
    MockLLMResponseProcessor.process_response = mock_process_response_error # type: ignore

    try:
        with caplog.at_level(logging.ERROR): # To see error from processor
            await llm_complete_handler.handle(event, agent_context)

        assert "Error occurred while using LLMResponseProcessor 'mock_processor': Simulated processor error." in caplog.text
        # Since processor errored, it didn't handle, so message should go to final queue
        assert "Publishing the current LLM response as a final message" in caplog.text
        
        agent_context.queues.assistant_final_message_queue.put.assert_any_call(response_text)
        agent_context.queues.assistant_final_message_queue.put.assert_any_call(END_OF_STREAM_SENTINEL)

    finally:
        MockLLMResponseProcessor.process_response = original_process_response # Restore original method

def test_llm_complete_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = LLMCompleteResponseReceivedEventHandler()
    assert "LLMCompleteResponseReceivedEventHandler initialized." in caplog.text
    assert handler.llm_response_processor_registry is not None # default registry is assigned

