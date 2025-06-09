import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.handlers.user_input_message_event_handler import UserInputMessageEventHandler
from autobyteus.agent.events.agent_events import UserMessageReceivedEvent, LLMUserMessageReadyEvent, GenericEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.agent.input_processor.base_user_input_processor import BaseAgentUserInputMessageProcessor
from autobyteus.agent.input_processor.processor_registry import AgentUserInputMessageProcessorRegistry, AgentUserInputMessageProcessorDefinition
from autobyteus.agent.message.context_file import ContextFile, ContextFileType


# Mock Input Processor
class MockInputProcessor(BaseAgentUserInputMessageProcessor):
    _processed_message_content = None
    _prefix_to_add = "Processed: "

    @classmethod
    def get_name(cls) -> str:
        return "mock_input_processor"

    async def process(self, message: AgentInputUserMessage, context) -> AgentInputUserMessage:
        MockInputProcessor._processed_message_content = message.content
        message.content = f"{self._prefix_to_add}{message.content}"
        message.metadata["processed_by"] = self.get_name()
        return message
    
    @classmethod
    def reset(cls):
        cls._processed_message_content = None

class AnotherMockInputProcessor(BaseAgentUserInputMessageProcessor):
    @classmethod
    def get_name(cls) -> str:
        return "another_mock_processor"
    async def process(self, message: AgentInputUserMessage, context) -> AgentInputUserMessage:
        message.content += " [Another]"
        message.metadata["another_processed_by"] = self.get_name()
        return message


@pytest.fixture
def user_input_handler(agent_context): 
    # Ensure a fresh registry for each test if it's a singleton
    if hasattr(AgentUserInputMessageProcessorRegistry, '_instance'): 
        AgentUserInputMessageProcessorRegistry._instance = None 
    registry = AgentUserInputMessageProcessorRegistry()

    MockInputProcessor.reset()
    mock_processor_def = AgentUserInputMessageProcessorDefinition(
        name="mock_input_processor", processor_class=MockInputProcessor 
    )
    another_mock_processor_def = AgentUserInputMessageProcessorDefinition(
        name="another_mock_processor", processor_class=AnotherMockInputProcessor 
    )
    registry.register_processor(mock_processor_def)
    registry.register_processor(another_mock_processor_def)
    
    handler = UserInputMessageEventHandler()
    handler.input_processor_registry = registry 

    return handler


@pytest.mark.asyncio
async def test_handle_user_input_no_processors(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test handling UserMessageReceivedEvent when no input processors are configured."""
    original_content = "Hello, agent!"
    image_urls = ["http://example.com/image.jpg"]
    context_files = [ContextFile(path="/test.txt", file_type=ContextFileType.TEXT)]
    metadata = {"user_id": "user123"}
    
    agent_input_msg = AgentInputUserMessage(content=original_content, image_urls=image_urls, context_files=context_files, metadata=metadata)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    agent_context.config.input_processor_names = [] 

    # agent_context.input_event_queues.enqueue_internal_system_event is already an AsyncMock

    with caplog.at_level(logging.DEBUG): 
        await user_input_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling UserMessageReceivedEvent: '{original_content[:100]}...'" in caplog.text
    assert "No input processors configured in agent specification." in caplog.text 
    assert f"Agent '{agent_context.agent_id}' processed AgentInputUserMessage (processors: []) and enqueued LLMUserMessageReadyEvent." in caplog.text 

    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    assert isinstance(enqueued_event.llm_user_message, LLMUserMessage)
    assert enqueued_event.llm_user_message.content == original_content
    assert enqueued_event.llm_user_message.image_urls == image_urls


@pytest.mark.asyncio
async def test_handle_user_input_with_one_processor(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test handling with one configured input processor."""
    original_content = "Needs processing."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    agent_context.config.input_processor_names = ["mock_input_processor"] 

    await user_input_handler.handle(event, agent_context)

    assert MockInputProcessor._processed_message_content == original_content 

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    expected_processed_content = f"{MockInputProcessor._prefix_to_add}{original_content}"
    assert enqueued_event.llm_user_message.content == expected_processed_content
    
    assert agent_input_msg.metadata["processed_by"] == "mock_input_processor"


@pytest.mark.asyncio
async def test_handle_user_input_with_multiple_processors(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test handling with multiple input processors applied sequentially."""
    original_content = "Sequential processing."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    agent_context.config.input_processor_names = ["mock_input_processor", "another_mock_processor"] 

    await user_input_handler.handle(event, agent_context)

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    expected_final_content = f"{MockInputProcessor._prefix_to_add}{original_content} [Another]"
    assert enqueued_event.llm_user_message.content == expected_final_content

    assert agent_input_msg.metadata["processed_by"] == "mock_input_processor"
    assert agent_input_msg.metadata["another_processed_by"] == "another_mock_processor"

@pytest.mark.asyncio
async def test_handle_processor_not_in_registry(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test behavior when a configured processor name is not in the registry."""
    original_content = "Unknown processor test."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    agent_context.config.input_processor_names = ["unknown_processor", "mock_input_processor"] 

    with caplog.at_level(logging.WARNING): 
        await user_input_handler.handle(event, agent_context)

    assert "Input processor name 'unknown_processor' not found in registry. Skipping." in caplog.text
    
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    expected_processed_content = f"{MockInputProcessor._prefix_to_add}{original_content}"
    assert enqueued_event.llm_user_message.content == expected_processed_content
    assert agent_input_msg.metadata["processed_by"] == "mock_input_processor"


@pytest.mark.asyncio
async def test_handle_processor_raises_exception(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test behavior when a processor's process method raises an exception."""
    original_content = "This will cause processor error."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    agent_context.config.input_processor_names = ["mock_input_processor", "another_mock_processor"] 

    async def mock_process_error(self, message, context):
        raise ValueError("Simulated processor error")

    original_process_method = MockInputProcessor.process
    MockInputProcessor.process = mock_process_error 

    try:
        with caplog.at_level(logging.ERROR): 
            await user_input_handler.handle(event, agent_context)

        assert "Error applying input processor 'mock_input_processor': Simulated processor error." in caplog.text
        assert "Skipping this processor and continuing with message from before this processor." in caplog.text

        enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
        assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
        expected_final_content = f"{original_content} [Another]" # mock_input_processor fails, original_content passed to another_mock_processor
        assert enqueued_event.llm_user_message.content == expected_final_content
        
        assert "processed_by" not in agent_input_msg.metadata 
        assert agent_input_msg.metadata["another_processed_by"] == "another_mock_processor"

    finally:
        MockInputProcessor.process = original_process_method 


@pytest.mark.asyncio
async def test_handle_invalid_event_type(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not UserMessageReceivedEvent."""
    invalid_event = GenericEvent(payload={}, type_name="some_other_event")

    with caplog.at_level(logging.WARNING):
        await user_input_handler.handle(invalid_event, agent_context) 
    
    assert f"UserInputMessageEventHandler received non-UserMessageReceivedEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()


def test_user_input_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = UserInputMessageEventHandler()
    assert "UserInputMessageEventHandler initialized." in caplog.text
    assert handler.input_processor_registry is not None
