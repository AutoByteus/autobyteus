# file: autobyteus/tests/unit_tests/agent_team/handlers/test_agent_team_event_handler_registry.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.handlers.agent_team_event_handler_registry import AgentTeamEventHandlerRegistry
from autobyteus.agent_team.handlers.base_agent_team_event_handler import BaseAgentTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import BaseAgentTeamEvent, AgentTeamReadyEvent

class DummyHandler(BaseAgentTeamEventHandler):
    async def handle(self, event, context): pass

def test_registry_register_and_get():
    """Tests basic registration and retrieval of a handler."""
    registry = AgentTeamEventHandlerRegistry()
    handler = DummyHandler()
    
    registry.register(AgentTeamReadyEvent, handler)
    
    assert registry.get_handler(AgentTeamReadyEvent) is handler
    assert registry.get_handler(BaseAgentTeamEvent) is None

def test_register_raises_for_invalid_type():
    """Tests that registration fails for a non-BaseAgentTeamEvent type."""
    registry = AgentTeamEventHandlerRegistry()
    handler = DummyHandler()
    
    with pytest.raises(TypeError):
        registry.register(str, handler)
