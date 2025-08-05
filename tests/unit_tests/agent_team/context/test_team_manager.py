# file: autobyteus/tests/unit_tests/agent_team/context/test_team_manager.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.context.team_manager import TeamManager
from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer
from autobyteus.agent_team.exceptions import TeamNodeNotFoundException

@pytest.fixture
def mock_runtime():
    """Provides a mocked AgentTeamRuntime."""
    runtime = MagicMock()
    runtime.context.get_node_config_by_name.return_value = None # Default to not found
    return runtime

@pytest.fixture
def mock_multiplexer():
    """Provides a mocked AgentEventMultiplexer."""
    return MagicMock(spec=AgentEventMultiplexer)

@pytest.fixture
def team_manager(mock_runtime, mock_multiplexer):
    """Provides a TeamManager instance with real dependencies for targeted patching."""
    return TeamManager(
        team_id="test_team",
        runtime=mock_runtime,
        multiplexer=mock_multiplexer
    )

@pytest.mark.asyncio
@patch('autobyteus.agent_team.context.team_manager.wait_for_agent_to_be_idle', new_callable=AsyncMock)
@patch('autobyteus.agent_team.context.team_manager.AgentFactory')
async def test_ensure_node_is_ready_lazy_creates_and_starts_agent(MockAgentFactory, mock_wait_idle, team_manager, mock_runtime, mock_multiplexer, team_node_factory):
    """
    Tests that ensure_node_is_ready lazy-creates an agent, starts it if not running, and bridges its events.
    """
    # --- Setup ---
    # Mock agent factory and the agent instance it will create
    mock_agent_factory_instance = MockAgentFactory.return_value
    mock_agent_instance = MagicMock()
    mock_agent_instance.is_running = False  # Simulate not running
    mock_agent_instance.agent_id = "agent_123"
    mock_agent_factory_instance.create_agent.return_value = mock_agent_instance
    
    # Mock the node config that the TeamManager will find
    node_name = "test_agent"
    node_config = team_node_factory(node_name)
    mock_runtime.context.get_node_config_by_name.return_value = node_config
    # Also set up coordinator node info for prompt injection check
    mock_runtime.context.config.coordinator_node = team_node_factory("other_agent")

    # --- Execute ---
    agent = await team_manager.ensure_node_is_ready(node_name)

    # --- Assert ---
    assert agent is mock_agent_instance
    
    # 1. Creation
    mock_runtime.context.get_node_config_by_name.assert_called_with(node_name)
    mock_agent_factory_instance.create_agent.assert_called_once()
    final_config_passed = mock_agent_factory_instance.create_agent.call_args.kwargs['config']
    assert isinstance(final_config_passed, AgentConfig)
    # Check that SendMessageTo tool was injected
    assert any(isinstance(t, patch.dict.get('autobyteus.agent_team.context.team_manager.SendMessageTo', MagicMock())) for t in final_config_passed.tools)

    # 2. Caching and Mapping
    assert team_manager._nodes_cache[node_name] is mock_agent_instance
    assert team_manager._agent_id_to_name_map[mock_agent_instance.agent_id] == node_name

    # 3. Bridging
    mock_multiplexer.start_bridging_agent_events.assert_called_once_with(mock_agent_instance, node_name)
    
    # 4. On-demand start
    mock_agent_instance.start.assert_called_once()
    mock_wait_idle.assert_awaited_once_with(mock_agent_instance, timeout=60.0)

@pytest.mark.asyncio
async def test_ensure_node_is_ready_returns_cached_and_running_node(team_manager, mock_agent):
    """
    Tests that if a node is already created and running, it's returned directly without further action.
    """
    node_name = "cached_agent"
    mock_agent.is_running = True
    team_manager._nodes_cache[node_name] = mock_agent

    # Ensure start and wait are not called
    with patch('autobyteus.agent_team.context.team_manager.wait_for_agent_to_be_idle') as mock_wait:
        agent = await team_manager.ensure_node_is_ready(node_name)
        assert agent is mock_agent
        mock_agent.start.assert_not_called()
        mock_wait.assert_not_called()

@pytest.mark.asyncio
async def test_ensure_node_is_ready_resolves_agent_id_to_name(team_manager, mock_agent):
    """
    Tests that an agent_id can be used to retrieve a cached node.
    """
    node_name = "my_agent"
    agent_id = "agent_abc_123"
    team_manager._agent_id_to_name_map[agent_id] = node_name
    team_manager._nodes_cache[node_name] = mock_agent
    
    agent = await team_manager.ensure_node_is_ready(agent_id)
    assert agent is mock_agent

@pytest.mark.asyncio
async def test_ensure_node_is_ready_throws_exception_for_unknown_node(team_manager):
    """
    Tests that TeamNodeNotFoundException is raised for a node that doesn't exist in the config.
    """
    with pytest.raises(TeamNodeNotFoundException, match="Node 'unknown_agent' not found in agent team 'test_team'"):
        await team_manager.ensure_node_is_ready("unknown_agent")
