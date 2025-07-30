# file: autobyteus/tests/unit_tests/workflow/context/test_team_manager.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.workflow.context.team_manager import TeamManager
from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.context import AgentConfig
from autobyteus.workflow.streaming.agent_event_multiplexer import AgentEventMultiplexer

@pytest.fixture
def mock_runtime():
    """Provides a mocked WorkflowRuntime."""
    return MagicMock()

@pytest.fixture
def mock_multiplexer():
    """Provides a mocked AgentEventMultiplexer."""
    return MagicMock(spec=AgentEventMultiplexer)

@pytest.fixture
def team_manager(mock_runtime, mock_multiplexer):
    """Provides a TeamManager instance with real dependencies for targeted patching."""
    return TeamManager(
        workflow_id="test_workflow",
        runtime=mock_runtime,
        multiplexer=mock_multiplexer
    )

@pytest.mark.asyncio
@patch('autobyteus.workflow.context.team_manager.wait_for_agent_to_be_idle', new_callable=AsyncMock)
async def test_ensure_agent_is_ready_starts_if_not_running(mock_wait_idle, team_manager, mock_multiplexer, mock_agent_config):
    """
    Tests that ensure_agent_is_ready starts the agent if it's not running.
    """
    mock_agent_factory = MagicMock(spec=AgentFactory)
    mock_agent_instance = MagicMock()
    mock_agent_instance.is_running = False # Simulate not running
    mock_agent_factory.create_agent.return_value = mock_agent_instance
    team_manager._agent_factory = mock_agent_factory

    configs = {"test_agent": mock_agent_config}
    team_manager.set_agent_configs(configs)

    agent = await team_manager.ensure_agent_is_ready("test_agent")

    assert agent is mock_agent_instance
    mock_agent_instance.start.assert_called_once()
    mock_wait_idle.assert_awaited_once_with(mock_agent_instance, timeout=60.0)

@pytest.mark.asyncio
@patch('autobyteus.workflow.context.team_manager.wait_for_agent_to_be_idle', new_callable=AsyncMock)
async def test_ensure_agent_is_ready_does_not_start_if_running(mock_wait_idle, team_manager, mock_multiplexer, mock_agent_config):
    """
    Tests that ensure_agent_is_ready does NOT start the agent if it's already running.
    """
    mock_agent_factory = MagicMock(spec=AgentFactory)
    mock_agent_instance = MagicMock()
    mock_agent_instance.is_running = True # Simulate already running
    mock_agent_factory.create_agent.return_value = mock_agent_instance
    team_manager._agent_factory = mock_agent_factory

    configs = {"test_agent": mock_agent_config}
    team_manager.set_agent_configs(configs)

    agent = await team_manager.ensure_agent_is_ready("test_agent")

    assert agent is mock_agent_instance
    mock_agent_instance.start.assert_not_called()
    mock_wait_idle.assert_not_awaited()
