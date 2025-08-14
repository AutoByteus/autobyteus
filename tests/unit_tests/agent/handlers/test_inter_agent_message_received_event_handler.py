import pytest
import logging
from unittest.mock import MagicMock, patch

from autobyteus.agent.handlers.inter_agent_message_event_handler import InterAgentMessageReceivedEventHandler
from autobyteus.agent.events.agent_events import InterAgentMessageReceivedEvent, LLMUserMessageReadyEvent, GenericEvent
from autobyteus.agent.message.inter_agent_message import InterAgentMessage, InterAgentMessageType
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def inter_agent_handler():
    return InterAgentMessageReceivedEventHandler()

@pytest.mark.asyncio
async def test_handle_inter_agent_message_success(inter_agent_handler: InterAgentMessageReceivedEventHandler, agent_context, caplog):
    """Test successful handling of an InterAgentMessageReceivedEvent."""
    sender_id = "sender_agent_123"
    content = "This is a test message from another agent."
    message_type = InterAgentMessageType.TASK_ASSIGNMENT
    # CORRECTED: Get role from agent_context.config, not agent_context.specification
    recipient_role = agent_context.config.role

    inter_agent_msg = InterAgentMessage(
        sender_agent_id=sender_id,
        recipient_agent_id=agent_context.agent_id, 
        recipient_role_name=recipient_role,
        content=content,
        message_type=message_type
    )
    event = InterAgentMessageReceivedEvent(inter_agent_message=inter_agent_msg)

    # agent_context.state.add_message_to_history is already a MagicMock
    # agent_context.input_event_queues.enqueue_internal_system_event is already an AsyncMock

    with caplog.at_level(logging.INFO):
        await inter_agent_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling InterAgentMessageReceivedEvent from sender '{sender_id}'" in caplog.text
    assert f"type '{message_type.value}'" in caplog.text
    # Updated assertion: removed [:100]... as the logger doesn't truncate/add ellipsis
    assert f"Content: '{content}'" in caplog.text 
    assert f"Agent '{agent_context.agent_id}' processed InterAgentMessage from sender '{sender_id}' and enqueued LLMUserMessageReadyEvent." in caplog.text 

    expected_history_content_part1 = f"You have received a message from another agent.\nSender Agent ID: {sender_id}"
    expected_history_content_part2 = f"Message Type: {message_type.value}"
    expected_history_content_part3 = f"--- Message Content ---\n{content}"
    
    agent_context.state.add_message_to_history.assert_called_once() 
    added_message = agent_context.state.add_message_to_history.call_args[0][0]
    assert added_message["role"] == "user"
    assert expected_history_content_part1 in added_message["content"]
    assert expected_history_content_part2 in added_message["content"]
    assert expected_history_content_part3 in added_message["content"]
    assert added_message["sender_agent_id"] == sender_id
    assert added_message["original_message_type"] == message_type.value

    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once() 
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent) 
    assert isinstance(enqueued_event.llm_user_message, LLMUserMessage)
    assert expected_history_content_part1 in enqueued_event.llm_user_message.content 
    assert expected_history_content_part2 in enqueued_event.llm_user_message.content
    assert expected_history_content_part3 in enqueued_event.llm_user_message.content

@pytest.mark.asyncio
async def test_handle_invalid_event_type(inter_agent_handler: InterAgentMessageReceivedEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not InterAgentMessageReceivedEvent."""
    invalid_event = GenericEvent(payload={"data": "test"}, type_name="wrong_event")

    with caplog.at_level(logging.WARNING):
        await inter_agent_handler.handle(invalid_event, agent_context) 

    assert f"InterAgentMessageReceivedEventHandler received an event of type {type(invalid_event).__name__}" in caplog.text
    assert "Skipping." in caplog.text
    agent_context.state.add_message_to_history.assert_not_called()
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

def test_inter_agent_handler_initialization(caplog):
    """Test initialization of the handler."""
    with caplog.at_level(logging.INFO):
        handler = InterAgentMessageReceivedEventHandler()
    assert "InterAgentMessageReceivedEventHandler initialized." in caplog.text
    assert isinstance(handler, InterAgentMessageReceivedEventHandler)
