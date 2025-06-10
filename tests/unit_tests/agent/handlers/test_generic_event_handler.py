# file: autobyteus/tests/unit_tests/agent/handlers/test_generic_event_handler.py
import pytest
import logging
from unittest.mock import MagicMock, patch

from autobyteus.agent.handlers.generic_event_handler import GenericEventHandler
from autobyteus.agent.events.agent_events import GenericEvent, UserMessageReceivedEvent # For testing non-generic event
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage # For UserMessageReceivedEvent payload

# Test Specific Event that is not GenericEvent
class NonGenericTestEvent:
    pass

@pytest.fixture
def generic_event_handler():
    return GenericEventHandler()

@pytest.mark.asyncio
async def test_handle_known_generic_event_type(generic_event_handler: GenericEventHandler, agent_context, caplog):
    """Test handling a GenericEvent with a known type_name."""
    event_payload = {"data": "some_data"}
    event_type_name = "example_custom_generic_event"
    event = GenericEvent(payload=event_payload, type_name=event_type_name)

    with caplog.at_level(logging.INFO):
        await generic_event_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling GenericEvent with type_name: '{event_type_name}'. Payload: {event_payload}" in caplog.text
    assert f"Handling specific generic event '{event_type_name}' for agent '{agent_context.agent_id}'." in caplog.text
    # Check that no warnings for unhandled type_name are present
    assert "unhandled type_name" not in caplog.text

@pytest.mark.asyncio
async def test_handle_another_known_generic_event_type(generic_event_handler: GenericEventHandler, agent_context, caplog):
    """Test handling a GenericEvent with another known type_name."""
    event_payload = {"key": "value"}
    event_type_name = "another_custom_event"
    event = GenericEvent(payload=event_payload, type_name=event_type_name)

    with caplog.at_level(logging.INFO):
        await generic_event_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling GenericEvent with type_name: '{event_type_name}'. Payload: {event_payload}" in caplog.text
    assert f"Handling specific generic event '{event_type_name}' for agent '{agent_context.agent_id}'." in caplog.text
    assert "unhandled type_name" not in caplog.text

@pytest.mark.asyncio
async def test_handle_unknown_generic_event_type(generic_event_handler: GenericEventHandler, agent_context, caplog):
    """Test handling a GenericEvent with an unknown type_name."""
    event_payload = {"info": "unknown_info"}
    event_type_name = "some_unknown_event_type"
    event = GenericEvent(payload=event_payload, type_name=event_type_name)
    
    with caplog.at_level(logging.WARNING):
        await generic_event_handler.handle(event, agent_context)
    
    # Check for the initial info log
    assert f"Agent '{agent_context.agent_id}' handling GenericEvent with type_name: '{event_type_name}'. Payload: {event_payload}" in caplog.text
    # Check for the warning log
    assert f"Agent '{agent_context.agent_id}' received GenericEvent with unhandled type_name: '{event_type_name}'." in caplog.text

@pytest.mark.asyncio
async def test_handle_non_generic_event(generic_event_handler: GenericEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not GenericEvent instances."""
    # Using UserMessageReceivedEvent as an example of a non-GenericEvent
    non_generic_event = UserMessageReceivedEvent(agent_input_user_message=AgentInputUserMessage(content="hello"))

    with caplog.at_level(logging.WARNING):
        await generic_event_handler.handle(non_generic_event, agent_context)

    # Check that a warning is logged about the wrong event type
    assert f"GenericEventHandler received a non-GenericEvent: {type(non_generic_event)}. Skipping." in caplog.text
    # Ensure no other processing logs (like "handling GenericEvent") appear
    assert f"handling GenericEvent with type_name" not in caplog.text

@pytest.mark.asyncio
async def test_handle_non_generic_event_completely_unrelated(generic_event_handler: GenericEventHandler, agent_context, caplog):
    """Test with a completely unrelated event type."""
    unrelated_event = NonGenericTestEvent()

    with caplog.at_level(logging.WARNING):
        await generic_event_handler.handle(unrelated_event, agent_context)
    
    assert f"GenericEventHandler received a non-GenericEvent: {type(unrelated_event)}. Skipping." in caplog.text

def test_generic_event_handler_initialization(caplog):
    """Test that the GenericEventHandler initializes with a log message."""
    with caplog.at_level(logging.INFO):
        handler = GenericEventHandler()
    assert "GenericEventHandler initialized." in caplog.text
    assert isinstance(handler, GenericEventHandler)
