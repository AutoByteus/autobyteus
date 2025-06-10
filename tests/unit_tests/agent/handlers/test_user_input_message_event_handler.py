import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.handlers.user_input_message_event_handler import UserInputMessageEventHandler
from autobyteus.agent.events.agent_events import UserMessageReceivedEvent, LLMUserMessageReadyEvent, GenericEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.agent.input_processor.base_user_input_processor import BaseAgentUserInputMessageProcessor
from autobyteus.agent.message.context_file import ContextFile, ContextFileType

# Mock Input Processor classes remain the same as they define behavior
class MockInputProcessor(BaseAgentUserInputMessageProcessor):
    def get_name(self) -> str:
        return "mock_input_processor"

    async def process(self, message: AgentInputUserMessage, context) -> AgentInputUserMessage:
        message.content = f"Processed: {message.content}"
        message.metadata["processed_by"] = self.get_name()
        return message

class AnotherMockInputProcessor(BaseAgentUserInputMessageProcessor):
    def get_name(self) -> str:
        return "another_mock_processor"

    async def process(self, message: AgentInputUserMessage, context) -> AgentInputUserMessage:
        message.content += " [Another]"
        message.metadata["another_processed_by"] = self.get_name()
        return message

@pytest.fixture
def user_input_handler(): 
    """Provides a fresh instance of the handler for each test."""
    return UserInputMessageEventHandler()

@pytest.mark.asyncio
async def test_handle_user_input_no_processors(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test handling UserMessageReceivedEvent when no input processors are configured."""
    original_content = "Hello, agent!"
    image_urls = ["http://example.com/image.jpg"]
    context_files = [ContextFile(path="/test.txt", file_type=ContextFileType.TEXT)]
    metadata = {"user_id": "user123"}
    
    agent_input_msg = AgentInputUserMessage(content=original_content, image_urls=image_urls, context_files=context_files, metadata=metadata)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    # Configure the context to have no processors
    agent_context.config.input_processors = [] 

    with caplog.at_level(logging.DEBUG): 
        await user_input_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling UserMessageReceivedEvent: '{original_content[:100]}...'" in caplog.text
    assert "No input processors configured in agent specification." in caplog.text 
    assert f"Agent '{agent_context.agent_id}' processed AgentInputUserMessage and enqueued LLMUserMessageReadyEvent." in caplog.text 

    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    assert isinstance(enqueued_event.llm_user_message, LLMUserMessage)
    assert enqueued_event.llm_user_message.content == original_content
    assert enqueued_event.llm_user_message.image_urls == image_urls

@pytest.mark.asyncio
async def test_handle_user_input_with_one_processor(user_input_handler: UserInputMessageEventHandler, agent_context):
    """Test handling with one configured input processor instance."""
    original_content = "Needs processing."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    # Provide an instance of the processor
    agent_context.config.input_processors = [MockInputProcessor()]

    await user_input_handler.handle(event, agent_context)

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    expected_processed_content = "Processed: Needs processing."
    assert enqueued_event.llm_user_message.content == expected_processed_content
    
    # The original message object is modified in-place
    assert agent_input_msg.metadata["processed_by"] == "mock_input_processor"

@pytest.mark.asyncio
async def test_handle_user_input_with_multiple_processors(user_input_handler: UserInputMessageEventHandler, agent_context):
    """Test handling with multiple input processor instances applied sequentially."""
    original_content = "Sequential processing."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    # Provide instances of the processors
    agent_context.config.input_processors = [MockInputProcessor(), AnotherMockInputProcessor()] 

    await user_input_handler.handle(event, agent_context)

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    expected_final_content = "Processed: Sequential processing. [Another]"
    assert enqueued_event.llm_user_message.content == expected_final_content

    assert agent_input_msg.metadata["processed_by"] == "mock_input_processor"
    assert agent_input_msg.metadata["another_processed_by"] == "another_mock_processor"

@pytest.mark.asyncio
async def test_handle_processor_raises_exception(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test behavior when a processor's process method raises an exception."""
    original_content = "This will cause processor error."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    # Mock one of the processors to raise an error
    error_processor = MockInputProcessor()
    error_processor.process = AsyncMock(side_effect=ValueError("Simulated processor error"))
    
    agent_context.config.input_processors = [error_processor, AnotherMockInputProcessor()]

    with caplog.at_level(logging.ERROR): 
        await user_input_handler.handle(event, agent_context)

    assert "Error applying input processor 'mock_input_processor': Simulated processor error." in caplog.text
    assert "Skipping this processor and continuing with message from before this processor." in caplog.text

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    # The first processor fails, so the second one processes the original content
    expected_final_content = f"{original_content} [Another]"
    assert enqueued_event.llm_user_message.content == expected_final_content
    
    assert "processed_by" not in agent_input_msg.metadata 
    assert agent_input_msg.metadata["another_processed_by"] == "another_mock_processor"

@pytest.mark.asyncio
async def test_handle_invalid_event_type(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not UserMessageReceivedEvent."""
    invalid_event = GenericEvent(payload={}, type_name="some_other_event")

    with caplog.at_level(logging.WARNING):
        await user_input_handler.handle(invalid_event, agent_context) 
    
    assert f"UserInputMessageEventHandler received non-UserMessageReceivedEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

def test_user_input_handler_initialization(caplog):
    """Tests the handler initializes without errors."""
    with caplog.at_level(logging.INFO):
        handler = UserInputMessageEventHandler()
    assert "UserInputMessageEventHandler initialized." in caplog.text
    # The handler no longer has a processor registry
    assert not hasattr(handler, 'input_processor_registry')
