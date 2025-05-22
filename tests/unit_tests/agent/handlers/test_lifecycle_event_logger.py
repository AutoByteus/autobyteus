import pytest
import logging
from unittest.mock import MagicMock, patch

from autobyteus.agent.handlers.lifecycle_event_logger import LifecycleEventLogger
from autobyteus.agent.events.agent_events import (
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    GenericEvent, # For testing unhandled LifecycleEvent
    UserMessageReceivedEvent # For testing non-LifecycleEvent
)
from autobyteus.agent.status import AgentStatus
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage # For UserMessageReceivedEvent


# Dummy LifecycleEvent for testing unhandled specific LifecycleEvents
class UnhandledLifecycleTestEvent(GenericEvent): # Re-using GenericEvent as a base for simplicity
    pass


@pytest.fixture
def lifecycle_logger_handler():
    return LifecycleEventLogger()

@pytest.mark.asyncio
async def test_handle_agent_started_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging of AgentStartedEvent."""
    event = AgentStartedEvent()
    agent_context.status = AgentStatus.STARTING # Typical status when this event is logged

    with caplog.at_level(logging.INFO):
        await lifecycle_logger_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' Logged AgentStartedEvent." in caplog.text
    assert f"Current status context holds: {AgentStatus.STARTING.value}" in caplog.text

@pytest.mark.asyncio
async def test_handle_agent_stopped_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging of AgentStoppedEvent."""
    event = AgentStoppedEvent()
    agent_context.status = AgentStatus.ENDED # Typical status

    with caplog.at_level(logging.INFO):
        await lifecycle_logger_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' Logged AgentStoppedEvent." in caplog.text
    assert f"Current status context holds: {AgentStatus.ENDED.value}" in caplog.text

@pytest.mark.asyncio
async def test_handle_agent_error_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging of AgentErrorEvent."""
    error_message = "A test error occurred."
    exception_details = "Traceback here."
    event = AgentErrorEvent(error_message=error_message, exception_details=exception_details)
    agent_context.status = AgentStatus.ERROR # Status would be ERROR

    with caplog.at_level(logging.ERROR): # AgentErrorEvent logs at ERROR level
        await lifecycle_logger_handler.handle(event, agent_context)

    log_output = caplog.text
    assert f"Agent '{agent_context.agent_id}' Logged AgentErrorEvent: {error_message}." in log_output
    assert f"Details: {exception_details}." in log_output
    assert f"Current status context holds: {AgentStatus.ERROR.value}" in log_output

@pytest.mark.asyncio
async def test_handle_unhandled_specific_lifecycle_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging for a LifecycleEvent subclass that isn't explicitly handled by specific if/elifs."""
    # We need to ensure UnhandledLifecycleTestEvent is treated as a LifecycleEvent.
    # Let's make it inherit from LifecycleEvent (from agent.events) indirectly if not directly.
    # For this test, we'll assume GenericEvent is a reasonable stand-in if it's a BaseEvent.
    # The handler checks `isinstance(event, LifecycleEvent)`.
    # For the test to correctly hit the "unhandled specific LifecycleEvent" path,
    # we'd need an event that *is* a LifecycleEvent but not AgentStarted, Stopped, or Error.
    # Let's create a mock for this.

    class MockLifecycleEvent(GenericEvent): # Still a BaseEvent, but not one of the specific ones
        pass
    
    # To make it a LifecycleEvent, it must inherit from it.
    # The original context for LifecycleEventLogger imports `from autobyteus.agent.events import ... LifecycleEvent`
    # So we can use that.
    from autobyteus.agent.events import LifecycleEvent as RealLifecycleEvent
    class AnotherLifecycleEvent(RealLifecycleEvent):
        pass


    unhandled_event = AnotherLifecycleEvent()
    agent_context.status = AgentStatus.RUNNING 

    with caplog.at_level(logging.WARNING):
        await lifecycle_logger_handler.handle(unhandled_event, agent_context)
    
    assert f"LifecycleEventLogger for agent '{agent_context.agent_id}' received an unhandled specific LifecycleEvent type: {type(unhandled_event)}." in caplog.text
    assert f"Current status: {AgentStatus.RUNNING.value}" in caplog.text

@pytest.mark.asyncio
async def test_handle_non_lifecycle_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging for an event that is not a LifecycleEvent at all."""
    non_lifecycle_event = UserMessageReceivedEvent(agent_input_user_message=AgentInputUserMessage(content="test"))
    agent_context.status = AgentStatus.IDLE

    with caplog.at_level(logging.WARNING):
        await lifecycle_logger_handler.handle(non_lifecycle_event, agent_context)

    assert f"LifecycleEventLogger for agent '{agent_context.agent_id}' received an unexpected event type: {type(non_lifecycle_event)}." in caplog.text
    assert f"Current status: {AgentStatus.IDLE.value}" in caplog.text

@pytest.mark.asyncio
async def test_handle_event_with_no_status_on_context(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test behavior if context.status is None (shouldn't happen with StatusManager)."""
    event = AgentStartedEvent()
    agent_context.status = None # Simulate status not being set

    with caplog.at_level(logging.INFO):
        await lifecycle_logger_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' Logged AgentStartedEvent." in caplog.text
    assert "Current status context holds: None" in caplog.text

