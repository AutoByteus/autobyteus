# file: autobyteus/tests/unit_tests/workflow/context/test_team_manager.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.workflow.context.team_manager import TeamManager
from autobyteus.agent.context import AgentConfig
from autobyteus.workflow.events.workflow_events import InterAgentMessageRequestEvent

@pytest.fixture
def mock_runtime():
    """Provides a mocked WorkflowRuntime."""
    runtime = MagicMock()
    runtime.submit_event = AsyncMock()
    return runtime

@pytest.fixture
def team_manager(mock_runtime):
    """Provides a TeamManager instance."""
    return TeamManager(workflow_id="test_workflow", runtime=mock_runtime)

@pytest.fixture
def mock_agent_config():
    """Provides a mocked AgentConfig."""
    return MagicMock(spec=AgentConfig)

@pytest.mark.asyncio
async def test_dispatch_inter_agent_message_request(team_manager, mock_runtime):
    """Tests that the dispatch method correctly calls the runtime's submit_event."""
    event = InterAgentMessageRequestEvent(
        sender_agent_id="sender1",
        recipient_name="receiver1",
        content="test",
        message_type="test"
    )
    await team_manager.dispatch_inter_agent_message_request(event)
    mock_runtime.submit_event.assert_awaited_once_with(event)

def test_get_agent_by_friendly_name_not_found(team_manager):
    """Tests that None is returned for an agent with no configuration."""
    assert team_manager.get_agent_by_friendly_name("non_existent") is None

@patch('autobyteus.workflow.context.team_manager.AgentFactory')
def test_get_agent_lazy_creation_and_caching(mock_agent_factory_cls, team_manager, mock_agent_config):
    """
    Tests lazy creation on the first call and retrieval from cache on the second.
    """
    mock_agent_instance = MagicMock()
    mock_agent_instance.context.custom_data = {} # Ensure custom_data exists
    mock_factory_instance = mock_agent_factory_cls.return_value
    mock_factory_instance.create_agent.return_value = mock_agent_instance

    configs = {"test_agent": mock_agent_config}
    team_manager.set_agent_configs(configs)

    # First call: should create the agent
    agent1 = team_manager.get_agent_by_friendly_name("test_agent")
    mock_factory_instance.create_agent.assert_called_once_with(config=mock_agent_config)
    assert agent1 is mock_agent_instance
    assert 'team_manager' in agent1.context.custom_data
    assert team_manager.get_all_agents() == [mock_agent_instance]

    # Second call: should return from cache
    agent2 = team_manager.get_agent_by_friendly_name("test_agent")
    mock_factory_instance.create_agent.assert_called_once() # Should still be 1 call
    assert agent2 is mock_agent_instance

@patch('autobyteus.workflow.context.team_manager.AgentFactory')
def test_get_and_configure_coordinator(mock_agent_factory_cls, team_manager, mock_agent_config):
    """Tests that the coordinator is correctly created and designated."""
    mock_agent_instance = MagicMock()
    mock_agent_instance.context.custom_data = {}
    mock_factory_instance = mock_agent_factory_cls.return_value
    mock_factory_instance.create_agent.return_value = mock_agent_instance
    
    configs = {"coordinator": mock_agent_config}
    team_manager.set_agent_configs(configs)

    coordinator = team_manager.get_and_configure_coordinator("coordinator")

    assert coordinator is mock_agent_instance
    assert team_manager.coordinator_agent is mock_agent_instance

def test_get_and_configure_coordinator_fails(team_manager):
    """Tests that an error is raised if the coordinator config is not found."""
    team_manager.set_agent_configs({}) # No configs
    with pytest.raises(ValueError, match="Could not create coordinator agent for name 'coordinator'"):
        team_manager.get_and_configure_coordinator("coordinator")
