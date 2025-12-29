# file: autobyteus/tests/unit_tests/agent_team/context/test_team_manager.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.context.team_manager import TeamManager
from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer
from autobyteus.agent_team.exceptions import TeamNodeNotFoundException
from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
from autobyteus.agent.agent import Agent
from autobyteus.agent_team.agent_team import AgentTeam

@pytest.fixture
def mock_runtime():
    """Provides a mocked AgentTeamRuntime."""
    runtime = MagicMock()
    runtime.context.get_node_config_by_name.return_value = None # Default to not found
    runtime.context.state.final_agent_configs = {} # Initialize the config dict
    return runtime

@pytest.fixture
def mock_multiplexer():
    """Provides a mocked AgentEventMultiplexer."""
    return MagicMock(spec=AgentEventMultiplexer)

@pytest.fixture
def team_manager(mock_runtime, mock_multiplexer):
    """Provides a TeamManager instance with mocked dependencies."""
    manager = TeamManager(
        team_id="test_team",
        runtime=mock_runtime,
        multiplexer=mock_multiplexer
    )
    return manager

@pytest.mark.asyncio
@patch('autobyteus.agent_team.context.team_manager.wait_for_agent_to_be_idle', new_callable=AsyncMock)
async def test_ensure_node_is_ready_uses_premade_config(mock_wait_idle, team_manager, mock_runtime, mock_multiplexer, agent_config_factory):
    """
    Tests that ensure_node_is_ready retrieves a pre-made config from state
    and uses it to create an agent.
    """
    # --- Setup ---
    # Create a mock agent that will be returned by the factory - use spec=Agent for isinstance checks
    mock_agent_instance = MagicMock(spec=Agent)
    mock_agent_instance.is_running = False
    mock_agent_instance.agent_id = "agent_123"
    mock_agent_instance.start = MagicMock()
    
    # Create a mock factory and patch the TeamManager's _agent_factory
    mock_agent_factory = MagicMock(spec=AgentFactory)
    mock_agent_factory.create_agent.return_value = mock_agent_instance
    team_manager._agent_factory = mock_agent_factory
    
    node_name = "test_agent"
    
    # Set up the pre-made config in the state
    premade_config = agent_config_factory(node_name)
    mock_runtime.context.state.final_agent_configs[node_name] = premade_config
    
    # Mock the node config wrapper
    node_config_wrapper = MagicMock()
    node_config_wrapper.is_sub_team = False
    mock_runtime.context.get_node_config_by_name.return_value = node_config_wrapper
    
    # --- Execute ---
    agent = await team_manager.ensure_node_is_ready(node_name)

    # --- Assert ---
    assert agent is mock_agent_instance
    
    # 1. Retrieval
    mock_runtime.context.get_node_config_by_name.assert_called_once_with(node_name)
    mock_agent_factory.create_agent.assert_called_once_with(config=premade_config)

    # 2. Caching and Mapping
    assert team_manager._nodes_cache[node_name] is mock_agent_instance
    assert team_manager._agent_id_to_name_map[mock_agent_instance.agent_id] == node_name

    # 3. Bridging
    mock_multiplexer.start_bridging_agent_events.assert_called_once_with(mock_agent_instance, node_name)
    mock_multiplexer.start_bridging_team_events.assert_not_called()
    
    # 4. On-demand start
    mock_agent_instance.start.assert_called_once()
    mock_wait_idle.assert_awaited_once_with(mock_agent_instance, timeout=60.0)

@pytest.mark.asyncio
@patch('autobyteus.agent_team.context.team_manager.wait_for_team_to_be_idle', new_callable=AsyncMock)
async def test_ensure_node_is_ready_creates_and_starts_sub_team(mock_wait_idle, team_manager, mock_runtime, mock_multiplexer):
    """
    Tests that ensure_node_is_ready correctly creates and starts a sub-team
    when the TeamNodeConfig indicates it's a sub-team.
    """
    # --- Setup --- use spec=AgentTeam so isinstance() check passes
    mock_sub_team_instance = MagicMock(spec=AgentTeam)
    mock_sub_team_instance.is_running = False
    mock_sub_team_instance.start = MagicMock()
    
    # Create a mock factory
    mock_team_factory = MagicMock()
    mock_team_factory.create_team.return_value = mock_sub_team_instance
    
    node_name = "test_sub_team"
    
    # Use spec=AgentTeamConfig so isinstance() check passes
    sub_team_config = MagicMock(spec=AgentTeamConfig)
    sub_team_config.name = node_name

    # Mock the node config wrapper
    node_config_wrapper = MagicMock()
    node_config_wrapper.is_sub_team = True
    node_config_wrapper.node_definition = sub_team_config
    mock_runtime.context.get_node_config_by_name.return_value = node_config_wrapper
    
    # Patch the AgentTeamFactory at import location - use create=True since it's a local import
    with patch('autobyteus.agent_team.factory.agent_team_factory.AgentTeamFactory', return_value=mock_team_factory):
        # --- Execute ---
        sub_team = await team_manager.ensure_node_is_ready(node_name)

    # --- Assert ---
    assert sub_team is mock_sub_team_instance
    
    mock_runtime.context.get_node_config_by_name.assert_called_once_with(node_name)
    mock_team_factory.create_team.assert_called_once_with(config=sub_team_config)
    
    assert team_manager._nodes_cache[node_name] is mock_sub_team_instance
    assert team_manager._agent_id_to_name_map == {}

    mock_multiplexer.start_bridging_team_events.assert_called_once_with(mock_sub_team_instance, node_name)
    mock_multiplexer.start_bridging_agent_events.assert_not_called()
    
    mock_sub_team_instance.start.assert_called_once()
    mock_wait_idle.assert_awaited_once_with(mock_sub_team_instance, timeout=120.0)

@pytest.mark.asyncio
async def test_ensure_node_is_ready_returns_cached_and_running_node(team_manager, mock_agent):
    """
    Tests that if a node is already created and running, it's returned directly without further action.
    """
    node_name = "cached_agent"
    mock_agent.is_running = True
    team_manager._nodes_cache[node_name] = mock_agent

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

@pytest.mark.asyncio
async def test_ensure_node_throws_if_premade_config_missing(team_manager, mock_runtime):
    """
    Tests that a runtime error occurs if the bootstrap step failed to create a config.
    """
    node_name = "forgotten_agent"
    node_config_wrapper = MagicMock()
    node_config_wrapper.is_sub_team = False
    mock_runtime.context.get_node_config_by_name.return_value = node_config_wrapper
    # Note: we do NOT add the config to `final_agent_configs`
    
    with pytest.raises(RuntimeError, match="No pre-prepared agent configuration found"):
        await team_manager.ensure_node_is_ready(node_name)
