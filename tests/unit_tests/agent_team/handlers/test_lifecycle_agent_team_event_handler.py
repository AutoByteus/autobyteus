# file: autobyteus/tests/unit_tests/agent_team/handlers/test_lifecycle_agent_team_event_handler.py
import logging
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.handlers.lifecycle_agent_team_event_handler import LifecycleAgentTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import AgentTeamReadyEvent, AgentTeamErrorEvent
from autobyteus.agent_team.context import AgentTeamContext

@pytest.fixture
def handler():
    return LifecycleAgentTeamEventHandler()

@pytest.mark.asyncio
async def test_handle_ready_event(handler: LifecycleAgentTeamEventHandler, agent_team_context: AgentTeamContext, caplog):
    """Tests that the ready event is logged correctly."""
    event = AgentTeamReadyEvent()
    with caplog.at_level(logging.INFO):
        await handler.handle(event, agent_team_context)
    
    assert f"Team '{agent_team_context.team_id}' Logged AgentTeamReadyEvent" in caplog.text

@pytest.mark.asyncio
async def test_handle_error_event(handler: LifecycleAgentTeamEventHandler, agent_team_context: AgentTeamContext, caplog):
    """Tests that the error event is logged correctly."""
    event = AgentTeamErrorEvent(error_message="A critical error", exception_details="Traceback...")
    with caplog.at_level(logging.ERROR):
        await handler.handle(event, agent_team_context)
    
    assert f"Team '{agent_team_context.team_id}' Logged AgentTeamErrorEvent: A critical error." in caplog.text
    assert "Details: Traceback..." in caplog.text
