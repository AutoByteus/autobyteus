# file: autobyteus/tests/unit_tests/agent_team/streaming/test_agent_event_multiplexer.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer
from autobyteus.agent_team.streaming.agent_event_bridge import AgentEventBridge
from autobyteus.agent_team.streaming.team_event_bridge import TeamEventBridge

@pytest.fixture
def mock_notifier():
    return MagicMock()

@pytest.fixture
def mock_worker():
    worker = MagicMock()
    worker.get_worker_loop.return_value = asyncio.get_running_loop()
    return worker

@pytest.fixture
def multiplexer(mock_notifier, mock_worker):
    return AgentEventMultiplexer(team_id="team-mux-test", notifier=mock_notifier, worker_ref=mock_worker)

@patch('autobyteus.agent_team.streaming.agent_event_multiplexer.AgentEventBridge')
def test_start_bridging_agent_creates_and_stores_bridge(MockAgentEventBridge, multiplexer: AgentEventMultiplexer):
    """
    Tests that start_bridging_agent_events correctly instantiates and stores an AgentEventBridge.
    """
    mock_agent = MagicMock()
    agent_name = "Agent1"

    multiplexer.start_bridging_agent_events(mock_agent, agent_name)

    MockAgentEventBridge.assert_called_once_with(
        agent=mock_agent,
        agent_name=agent_name,
        notifier=multiplexer._notifier,
        loop=multiplexer._get_loop()
    )
    assert agent_name in multiplexer._agent_bridges
    assert multiplexer._agent_bridges[agent_name] is MockAgentEventBridge.return_value

@patch('autobyteus.agent_team.streaming.agent_event_multiplexer.TeamEventBridge')
def test_start_bridging_team_creates_and_stores_bridge(MockTeamEventBridge, multiplexer: AgentEventMultiplexer):
    """
    Tests that start_bridging_team_events correctly instantiates and stores a TeamEventBridge.
    """
    mock_team = MagicMock()
    node_name = "SubTeam1"

    multiplexer.start_bridging_team_events(mock_team, node_name)

    MockTeamEventBridge.assert_called_once_with(
        sub_team=mock_team,
        sub_team_node_name=node_name,
        parent_notifier=multiplexer._notifier,
        loop=multiplexer._get_loop()
    )
    assert node_name in multiplexer._team_bridges
    assert multiplexer._team_bridges[node_name] is MockTeamEventBridge.return_value

@pytest.mark.asyncio
@patch('autobyteus.agent_team.streaming.agent_event_multiplexer.AgentEventBridge')
@patch('autobyteus.agent_team.streaming.agent_event_multiplexer.TeamEventBridge')
async def test_shutdown_cancels_all_bridges(MockTeamEventBridge, MockAgentEventBridge, multiplexer: AgentEventMultiplexer):
    """
    Tests that the shutdown method calls cancel() on all active bridges.
    """
    agent_bridge = MockAgentEventBridge.return_value
    agent_bridge.cancel = AsyncMock()
    team_bridge = MockTeamEventBridge.return_value
    team_bridge.cancel = AsyncMock()

    multiplexer._agent_bridges = {"Agent1": agent_bridge}
    multiplexer._team_bridges = {"SubTeam1": team_bridge}

    await multiplexer.shutdown()

    agent_bridge.cancel.assert_awaited_once()
    team_bridge.cancel.assert_awaited_once()
    assert len(multiplexer._agent_bridges) == 0
    assert len(multiplexer._team_bridges) == 0
