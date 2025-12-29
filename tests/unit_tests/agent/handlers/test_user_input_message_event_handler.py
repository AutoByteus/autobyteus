import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.handlers.user_input_message_event_handler import UserInputMessageEventHandler
from autobyteus.agent.events.agent_events import UserMessageReceivedEvent, LLMUserMessageReadyEvent, GenericEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.agent.input_processor.base_user_input_processor import BaseAgentUserInputMessageProcessor
from autobyteus.agent.message.context_file import ContextFile, ContextFileType
from autobyteus.agent.events.notifiers import AgentExternalEventNotifier
from autobyteus.agent.sender_type import SenderType, TASK_NOTIFIER_SENDER_ID


# Mock Input Processor classes
class MockInputProcessor(BaseAgentUserInputMessageProcessor):
    async def process(self, message: AgentInputUserMessage, context, triggering_event: UserMessageReceivedEvent) -> AgentInputUserMessage:
        message.content = f"Processed: {message.content}"
        message.metadata["processed_by"] = self.get_name()
        return message

class AnotherMockInputProcessor(BaseAgentUserInputMessageProcessor):
    async def process(self, message: AgentInputUserMessage, context, triggering_event: UserMessageReceivedEvent) -> AgentInputUserMessage:
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
    image_url = "http://example.com/image.jpg"
    
    # Correctly create AgentInputUserMessage with ContextFile for image
    agent_input_msg = AgentInputUserMessage(
        content=original_content,
        context_files=[ContextFile(uri=image_url, file_type=ContextFileType.IMAGE)],
        metadata={"user_id": "user123"}
    )
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    agent_context.config.input_processors = [] 

    with caplog.at_level(logging.DEBUG): 
        await user_input_handler.handle(event, agent_context)

    # Assert updated log message 
    assert f"Agent '{agent_context.agent_id}' handling UserMessageReceivedEvent (type: user): '{original_content}'" in caplog.text
    assert "No input processors configured in agent config." in caplog.text
    assert f"Agent '{agent_context.agent_id}' processed AgentInputUserMessage and enqueued LLMUserMessageReadyEvent." in caplog.text 

    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    
    # Assert final LLMUserMessage is correctly built
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    llm_user_message = enqueued_event.llm_user_message
    assert isinstance(llm_user_message, LLMUserMessage)
    assert llm_user_message.content == original_content
    assert llm_user_message.image_urls == [image_url]

@pytest.mark.asyncio
async def test_handle_user_input_with_one_processor(user_input_handler: UserInputMessageEventHandler, agent_context):
    """Test handling with one configured input processor instance."""
    original_content = "Needs processing."
    agent_input_msg = AgentInputUserMessage(content=original_content, sender_type=SenderType.USER)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)
    agent_context.config.input_processors = [MockInputProcessor()]

    await user_input_handler.handle(event, agent_context)

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    expected_processed_content = "Processed: Needs processing."
    assert enqueued_event.llm_user_message.content == expected_processed_content
    assert enqueued_event.llm_user_message.content == expected_processed_content
    # Original message metadata is not modified due to deepcopy in handler
    # assert agent_input_msg.metadata["processed_by"] == "MockInputProcessor"

@pytest.mark.asyncio
async def test_handle_user_input_with_multiple_processors(user_input_handler: UserInputMessageEventHandler, agent_context):
    """Test handling with multiple input processor instances applied sequentially."""
    original_content = "Sequential processing."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)
    agent_context.config.input_processors = [MockInputProcessor(), AnotherMockInputProcessor()] 

    await user_input_handler.handle(event, agent_context)

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    expected_final_content = "Processed: Sequential processing. [Another]"
    assert enqueued_event.llm_user_message.content == expected_final_content
    expected_final_content = "Processed: Sequential processing. [Another]"
    assert enqueued_event.llm_user_message.content == expected_final_content
    # Original message metadata is not modified due to deepcopy in handler
    # assert agent_input_msg.metadata["processed_by"] == "MockInputProcessor"
    # assert agent_input_msg.metadata["another_processed_by"] == "AnotherMockInputProcessor"

@pytest.mark.asyncio
async def test_handle_processor_raises_exception(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test behavior when a processor's process method raises an exception."""
    original_content = "This will cause processor error."
    agent_input_msg = AgentInputUserMessage(content=original_content)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    error_processor = MockInputProcessor()
    error_processor.process = AsyncMock(side_effect=ValueError("Simulated processor error"))
    agent_context.config.input_processors = [error_processor, AnotherMockInputProcessor()]

    with caplog.at_level(logging.ERROR): 
        await user_input_handler.handle(event, agent_context)

    assert "Error applying input processor 'MockInputProcessor': Simulated processor error." in caplog.text
    assert "Skipping this processor and continuing with message from before this processor." in caplog.text

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    expected_final_content = f"{original_content} [Another]"
    assert enqueued_event.llm_user_message.content == expected_final_content
    expected_final_content = f"{original_content} [Another]"
    assert enqueued_event.llm_user_message.content == expected_final_content
    # Original message metadata is not modified due to deepcopy in handler
    # assert "processed_by" not in agent_input_msg.metadata 
    # assert agent_input_msg.metadata["another_processed_by"] == "AnotherMockInputProcessor"

@pytest.mark.asyncio
async def test_handle_invalid_event_type(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not UserMessageReceivedEvent."""
    invalid_event = GenericEvent(payload={}, type_name="some_other_event")

    with caplog.at_level(logging.WARNING):
        await user_input_handler.handle(invalid_event, agent_context) 
    
    assert f"UserInputMessageEventHandler received non-UserMessageReceivedEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_handle_system_notification_by_sender_type(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test handling of system notifications via sender_type."""
    system_notification_content = "Your task is now ready."
    agent_input_msg = AgentInputUserMessage(
        content=system_notification_content,
        sender_type=SenderType.SYSTEM,
        metadata={'sender_id': TASK_NOTIFIER_SENDER_ID}
    )
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)

    # Ensure notifier is present
    mock_notifier = AsyncMock(spec=AgentExternalEventNotifier)
    agent_context.status_manager.notifier = mock_notifier
    agent_context.config.input_processors = []

    with caplog.at_level(logging.INFO):
        await user_input_handler.handle(event, agent_context)

    mock_notifier.notify_agent_data_system_task_notification_received.assert_called_once_with({
        "sender_id": TASK_NOTIFIER_SENDER_ID,
        "content": system_notification_content,
    })
    assert "emitted system task notification for TUI based on SYSTEM sender_type" in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()

@pytest.mark.asyncio
async def test_handle_message_from_tool(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test that a message from a tool is handled and logged correctly."""
    tool_result_content = "Tool result: 42"
    agent_input_msg = AgentInputUserMessage(content=tool_result_content, sender_type=SenderType.TOOL)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)
    agent_context.config.input_processors = []

    with caplog.at_level(logging.INFO):
        await user_input_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling UserMessageReceivedEvent (type: tool): '{tool_result_content}'" in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()

@pytest.mark.asyncio
async def test_handle_message_from_agent(user_input_handler: UserInputMessageEventHandler, agent_context, caplog):
    """Test that a message from another agent is handled and logged correctly."""
    inter_agent_content = "Hello from another agent."
    agent_input_msg = AgentInputUserMessage(content=inter_agent_content, sender_type=SenderType.AGENT)
    event = UserMessageReceivedEvent(agent_input_user_message=agent_input_msg)
    agent_context.config.input_processors = []

    with caplog.at_level(logging.INFO):
        await user_input_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling UserMessageReceivedEvent (type: agent): '{inter_agent_content}'" in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()

def test_user_input_handler_initialization(caplog):
    """Tests the handler initializes without errors."""
    with caplog.at_level(logging.INFO):
        handler = UserInputMessageEventHandler()
    assert "UserInputMessageEventHandler initialized." in caplog.text
