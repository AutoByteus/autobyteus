import pytest
import logging
from unittest.mock import MagicMock, patch

from autobyteus.agent.handlers.lifecycle_event_logger import LifecycleEventLogger
from autobyteus.agent.events.agent_events import (
    AgentReadyEvent, # UPDATED
    AgentStoppedEvent,
    AgentErrorEvent,
    GenericEvent, 
    UserMessageReceivedEvent,
    LifecycleEvent # Import base LifecycleEvent
)
from autobyteus.agent.context.phases import AgentOperationalPhase # Import new phase enum
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage 


# Dummy LifecycleEvent for testing unhandled specific LifecycleEvents
class UnhandledRealLifecycleEvent(LifecycleEvent): # Inherit from Real LifecycleEvent
    pass


@pytest.fixture
def lifecycle_logger_handler():
    return LifecycleEventLogger()

@pytest.mark.asyncio
async def test_handle_agent_ready_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog): # RENAMED test
    """Test logging of AgentReadyEvent."""
    event = AgentReadyEvent() # UPDATED event type
    agent_context.current_phase = AgentOperationalPhase.IDLE # Typical phase when this event is logged

    with caplog.at_level(logging.INFO):
        await lifecycle_logger_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' Logged AgentReadyEvent." in caplog.text # UPDATED log message
    assert f"Current agent phase: {AgentOperationalPhase.IDLE.value}" in caplog.text # UPDATED status to phase

@pytest.mark.asyncio
async def test_handle_agent_stopped_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging of AgentStoppedEvent."""
    event = AgentStoppedEvent()
    agent_context.current_phase = AgentOperationalPhase.SHUTDOWN_COMPLETE # Typical phase

    with caplog.at_level(logging.INFO):
        await lifecycle_logger_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' Logged AgentStoppedEvent." in caplog.text
    assert f"Current agent phase: {AgentOperationalPhase.SHUTDOWN_COMPLETE.value}" in caplog.text # UPDATED

@pytest.mark.asyncio
async def test_handle_agent_error_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging of AgentErrorEvent."""
    error_message = "A test error occurred."
    exception_details = "Traceback here."
    event = AgentErrorEvent(error_message=error_message, exception_details=exception_details)
    agent_context.current_phase = AgentOperationalPhase.ERROR # Phase would be ERROR

    with caplog.at_level(logging.ERROR): 
        await lifecycle_logger_handler.handle(event, agent_context)

    log_output = caplog.text
    assert f"Agent '{agent_context.agent_id}' Logged AgentErrorEvent: {error_message}." in log_output
    assert f"Details: {exception_details}." in log_output
    assert f"Current agent phase: {AgentOperationalPhase.ERROR.value}" in log_output # UPDATED

@pytest.mark.asyncio
async def test_handle_unhandled_specific_lifecycle_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging for a LifecycleEvent subclass that isn't explicitly handled."""
    unhandled_event = UnhandledRealLifecycleEvent() # Use our custom LifecycleEvent subclass
    agent_context.current_phase = AgentOperationalPhase.PROCESSING_USER_INPUT 

    with caplog.at_level(logging.WARNING):
        await lifecycle_logger_handler.handle(unhandled_event, agent_context)
    
    assert f"LifecycleEventLogger for agent '{agent_context.agent_id}' received an unhandled specific LifecycleEvent type: {type(unhandled_event)}." in caplog.text
    assert f"Current phase: {AgentOperationalPhase.PROCESSING_USER_INPUT.value}" in caplog.text # UPDATED

@pytest.mark.asyncio
async def test_handle_non_lifecycle_event(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog):
    """Test logging for an event that is not a LifecycleEvent at all."""
    non_lifecycle_event = UserMessageReceivedEvent(agent_input_user_message=AgentInputUserMessage(content="test"))
    agent_context.current_phase = AgentOperationalPhase.IDLE

    with caplog.at_level(logging.WARNING):
        await lifecycle_logger_handler.handle(non_lifecycle_event, agent_context)

    assert f"LifecycleEventLogger for agent '{agent_context.agent_id}' received an unexpected event type: {type(non_lifecycle_event)}." in caplog.text
    assert f"Current phase: {AgentOperationalPhase.IDLE.value}" in caplog.text # UPDATED

@pytest.mark.asyncio
async def test_handle_event_with_no_phase_on_context(lifecycle_logger_handler: LifecycleEventLogger, agent_context, caplog): # RENAMED test
    """Test behavior if context.current_phase is None."""
    event = AgentReadyEvent() # UPDATED
    agent_context.current_phase = None # Simulate phase not being set

    with caplog.at_level(logging.INFO):
        await lifecycle_logger_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' Logged AgentReadyEvent." in caplog.text # UPDATED
    assert "Current agent phase: None (Phase not set)" in caplog.text
