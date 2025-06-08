import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

from autobyteus.agent.handlers.llm_complete_response_received_event_handler import LLMCompleteResponseReceivedEventHandler
from autobyteus.agent.events.agent_events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.agent.llm_response_processor.base_processor import BaseLLMResponseProcessor
from autobyteus.agent.llm_response_processor.processor_registry import LLMResponseProcessorRegistry, LLMResponseProcessorDefinition
from autobyteus.llm.utils.response_types import CompleteResponse # For type checking
from autobyteus.agent.tool_invocation import ToolInvocation # Import for spec


# Mock LLM Response Processor
class MockLLMResponseProcessor(BaseLLMResponseProcessor):
    _should_handle = False
    _processed_text = None
    _enqueued_event = None # This was for old queue system, not directly relevant for notifier

    @classmethod
    def get_name(cls) -> str:
        return "mock_processor"

    async def process_response(self, response: str, context) -> bool:
        MockLLMResponseProcessor._processed_text = response
        if MockLLMResponseProcessor._should_handle:
            # Simulate that the processor took action, e.g., by enqueuing a tool invocation event
            # In a real scenario, it would enqueue to context.input_event_queues
            
            # Create a mock for ToolInvocation that behaves as expected for .name
            mock_ti = MagicMock(spec=ToolInvocation)
            mock_ti.id = "test-tool-id"
            mock_ti.name = "processed_tool" # Ensure .name returns the string
            # mock_ti.arguments can be left as default MagicMock or set if needed by other assertions

            await context.input_event_queues.enqueue_tool_invocation_request(
                PendingToolInvocationEvent(tool_invocation=mock_ti)
            )
            return True
        return False

    @classmethod
    def reset(cls):
        cls._should_handle = False
        cls._processed_text = None
        cls._enqueued_event = None


@pytest.fixture
def llm_complete_handler(agent_context): 
    registry = LLMResponseProcessorRegistry() 
    if hasattr(LLMResponseProcessorRegistry, '_instance'): # Access private _instance if using SingletonMeta directly
        LLMResponseProcessorRegistry._instance = None 
    registry = LLMResponseProcessorRegistry()


    MockLLMResponseProcessor.reset() 
    mock_processor_def = LLMResponseProcessorDefinition(
        name="mock_processor",
        processor_class=MockLLMResponseProcessor 
    )
    registry.register_processor(mock_processor_def)
    
    handler = LLMCompleteResponseReceivedEventHandler()
    handler.llm_response_processor_registry = registry 

    agent_context.definition.llm_response_processor_names = ["mock_processor"]
    # Ensure notifier is mocked on phase_manager
    if not hasattr(agent_context.phase_manager, 'notifier') or not isinstance(agent_context.phase_manager.notifier, MagicMock):
        agent_context.phase_manager.notifier = AsyncMock() # Use AsyncMock for notifier methods
    return handler


@pytest.mark.asyncio
async def test_handle_response_processed_by_processor(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test when an LLMResponseProcessor handles the response."""
    response_text = "LLM response with tool call <tool>..."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)

    MockLLMResponseProcessor._should_handle = True 

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling LLMCompleteResponseReceivedEvent." in caplog.text
    assert f"Agent '{agent_context.agent_id}': LLMResponseProcessor 'mock_processor' handled the response" in caplog.text
    
    assert MockLLMResponseProcessor._processed_text == response_text
    
    # Assert that the notifier was NOT called for assistant_complete_response
    agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.assert_not_called()
    
    # Assert that the mock processor enqueued its event (as per its mocked logic)
    agent_context.input_event_queues.enqueue_tool_invocation_request.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert isinstance(enqueued_event, PendingToolInvocationEvent)
    assert enqueued_event.tool_invocation.name == "processed_tool"


@pytest.mark.asyncio
async def test_handle_response_not_processed_by_any_processor(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test when no LLMResponseProcessor handles the response."""
    response_text = "Final LLM answer, no tools."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)

    MockLLMResponseProcessor._should_handle = False 

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling LLMCompleteResponseReceivedEvent." in caplog.text
    assert "No LLMResponseProcessor handled the response." in caplog.text
    assert f"Emitting the current LLM response as a complete response for this leg." in caplog.text # Updated log
    
    assert MockLLMResponseProcessor._processed_text == response_text
    
    # Assert notifier was called with the correct CompleteResponse object
    agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()
    called_arg = agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.call_args[0][0]
    assert isinstance(called_arg, CompleteResponse)
    assert called_arg.content == response_text


@pytest.mark.asyncio
async def test_handle_error_response_event(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test when the event itself indicates an error response."""
    error_text = "An error occurred in a previous stage."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=error_text, is_error=True)

    MockLLMResponseProcessor._should_handle = False 

    with caplog.at_level(logging.INFO):
        await llm_complete_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling LLMCompleteResponseReceivedEvent." in caplog.text
    assert "LLMCompleteResponseReceivedEvent was marked as an error response." in caplog.text
    assert "Skipping LLMResponseProcessor attempts." in caplog.text
    assert f"emitting a received error message as a complete response" in caplog.text # Updated log

    assert MockLLMResponseProcessor._processed_text is None 
    
    agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()
    called_arg = agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.call_args[0][0]
    assert isinstance(called_arg, CompleteResponse)
    assert called_arg.content == error_text


@pytest.mark.asyncio
async def test_handle_no_processors_configured(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test behavior when agent_definition has no llm_response_processor_names."""
    response_text = "Response when no processors are configured."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)
    
    agent_context.definition.llm_response_processor_names = [] 

    MockLLMResponseProcessor._should_handle = False 

    with caplog.at_level(logging.DEBUG): 
        await llm_complete_handler.handle(event, agent_context)

    assert "No llm_response_processor_names configured in agent definition." in caplog.text
    assert "Emitting the current LLM response as a complete response for this leg." in caplog.text # Updated log

    assert MockLLMResponseProcessor._processed_text is None
    
    agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()
    called_arg = agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.call_args[0][0]
    assert isinstance(called_arg, CompleteResponse)
    assert called_arg.content == response_text


@pytest.mark.asyncio
async def test_handle_processor_not_in_registry(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test behavior when a configured processor name is not in the registry."""
    response_text = "Response with unknown processor."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)
    
    agent_context.definition.llm_response_processor_names = ["unknown_processor", "mock_processor"]
    MockLLMResponseProcessor._should_handle = False 

    with caplog.at_level(logging.DEBUG): 
        await llm_complete_handler.handle(event, agent_context)

    assert "LLMResponseProcessor name 'unknown_processor' defined in agent_definition not found in registry." in caplog.text
    assert "LLMResponseProcessor 'mock_processor' did not handle the response." in caplog.text
    assert "Emitting the current LLM response as a complete response for this leg." in caplog.text 

    agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()
    called_arg = agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.call_args[0][0]
    assert isinstance(called_arg, CompleteResponse)
    assert called_arg.content == response_text


@pytest.mark.asyncio
async def test_handle_processor_raises_exception(llm_complete_handler: LLMCompleteResponseReceivedEventHandler, agent_context, caplog):
    """Test behavior when a processor's process_response method raises an exception."""
    response_text = "Response that causes processor error."
    event = LLMCompleteResponseReceivedEvent(complete_response_text=response_text)
    
    agent_context.definition.llm_response_processor_names = ["mock_processor"]
    
    async def mock_process_response_error(self, response, context):
        raise ValueError("Simulated processor error")

    original_process_response = MockLLMResponseProcessor.process_response
    MockLLMResponseProcessor.process_response = mock_process_response_error 

    try:
        with caplog.at_level(logging.INFO): # Changed from ERROR to INFO
            await llm_complete_handler.handle(event, agent_context)

        assert "Error occurred while using LLMResponseProcessor 'mock_processor': Simulated processor error." in caplog.text
        assert "Emitting the current LLM response as a complete response for this leg." in caplog.text
        
        agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.assert_called_once()
        called_arg = agent_context.phase_manager.notifier.notify_agent_data_assistant_complete_response.call_args[0][0]
        assert isinstance(called_arg, CompleteResponse)
        assert called_arg.content == response_text
        
        # Also check that the error_output_generation notifier was called
        agent_context.phase_manager.notifier.notify_agent_error_output_generation.assert_called_once_with(
            error_source="LLMResponseProcessor.mock_processor",
            error_message="Simulated processor error"
        )

    finally:
        MockLLMResponseProcessor.process_response = original_process_response

def test_llm_complete_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = LLMCompleteResponseReceivedEventHandler()
    assert "LLMCompleteResponseReceivedEventHandler initialized." in caplog.text
    assert handler.llm_response_processor_registry is not None

