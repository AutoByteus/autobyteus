# file: autobyteus/tests/unit_tests/agent_team/task_notification/test_task_activator.py
"""
Unit tests for the TaskActivator class.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent_team.task_notification.task_activator import TaskActivator
from autobyteus.agent_team.events import ProcessUserMessageEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

@pytest.fixture
def mock_team_manager():
    """Provides a mock TeamManager."""
    manager = MagicMock()
    manager.team_id = "test_activator_team"
    manager.ensure_node_is_ready = AsyncMock()
    manager.dispatch_user_message_to_agent = AsyncMock()
    return manager

def test_initialization_with_valid_manager(mock_team_manager):
    """Tests successful initialization."""
    activator = TaskActivator(team_manager=mock_team_manager)
    assert activator._team_manager is not None

def test_initialization_raises_error_with_none_manager():
    """Tests that initialization fails if TeamManager is None."""
    with pytest.raises(ValueError):
        TaskActivator(team_manager=None)

@pytest.mark.asyncio
async def test_activate_agent_happy_path(mock_team_manager):
    """
    Tests the successful activation of an agent, verifying the calls made to
    the TeamManager.
    """
    activator = TaskActivator(team_manager=mock_team_manager)
    agent_name = "AgentToActivate"
    
    await activator.activate_agent(agent_name)
    
    # Verify that the agent was made ready first
    mock_team_manager.ensure_node_is_ready.assert_awaited_once_with(agent_name)
    
    # Verify that the message was dispatched
    mock_team_manager.dispatch_user_message_to_agent.assert_awaited_once()
    
    # Inspect the dispatched event
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    assert isinstance(dispatched_event, ProcessUserMessageEvent)
    assert dispatched_event.target_agent_name == agent_name
    
    # Inspect the message content
    user_message = dispatched_event.user_message
    assert isinstance(user_message, AgentInputUserMessage)
    assert "You have new tasks" in user_message.content
    assert user_message.metadata['source'] == 'system_task_notifier'

@pytest.mark.asyncio
async def test_activate_agent_handles_team_manager_exception(mock_team_manager, caplog):
    """
    Tests that the activator logs an error but does not crash if the
    TeamManager raises an exception.
    """
    error_message = "Node failed to start"
    mock_team_manager.ensure_node_is_ready.side_effect = RuntimeError(error_message)
    
    activator = TaskActivator(team_manager=mock_team_manager)
    agent_name = "AgentThatFails"
    
    # The method should complete without raising an exception itself
    await activator.activate_agent(agent_name)
    
    # Verify an error was logged
    assert "ERROR" in caplog.text
    assert f"Failed to activate agent '{agent_name}'" in caplog.text
    assert error_message in caplog.text
    
    # Verify the message dispatch was not attempted
    mock_team_manager.dispatch_user_message_to_agent.assert_not_called()
