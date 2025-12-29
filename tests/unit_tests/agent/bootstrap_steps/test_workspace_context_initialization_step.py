# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_workspace_context_initialization_step.py
import pytest
import logging
from unittest.mock import MagicMock

from autobyteus.agent.bootstrap_steps.workspace_context_initialization_step import WorkspaceContextInitializationStep
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.agent.context import AgentContext
from autobyteus.agent.status.manager import AgentStatusManager

@pytest.fixture
def workspace_init_step():
    """Provides a clean instance of WorkspaceContextInitializationStep."""
    return WorkspaceContextInitializationStep()

@pytest.fixture
def mock_workspace():
    """Provides a mock workspace object with a set_context method."""
    workspace = MagicMock(spec=BaseAgentWorkspace)
    # The set_context method doesn't need to be async
    workspace.set_context = MagicMock()
    return workspace

@pytest.mark.asyncio
async def test_execute_success_with_workspace(
    workspace_init_step: WorkspaceContextInitializationStep,
    agent_context: AgentContext,
    mock_workspace: BaseAgentWorkspace,
    mock_status_manager
):
    """Tests successful execution when a workspace is configured."""
    agent_context.state.workspace = mock_workspace

    success = await workspace_init_step.execute(agent_context, mock_status_manager)

    assert success is True
    # Verify set_context was called with the correct context
    mock_workspace.set_context.assert_called_once_with(agent_context)

@pytest.mark.asyncio
async def test_execute_success_no_workspace(
    workspace_init_step: WorkspaceContextInitializationStep,
    agent_context: AgentContext,
    mock_status_manager,
    caplog
):
    """Tests graceful pass-through when no workspace is configured."""
    agent_context.state.workspace = None

    with caplog.at_level(logging.DEBUG):
        success = await workspace_init_step.execute(agent_context, mock_status_manager)

    assert success is True
    assert f"Agent '{agent_context.agent_id}': No workspace configured. Skipping context injection." in caplog.text

@pytest.mark.asyncio
async def test_execute_warns_if_no_set_context_method(
    workspace_init_step: WorkspaceContextInitializationStep,
    agent_context: AgentContext,
    mock_status_manager,
    caplog
):
    """Tests that a warning is logged if the workspace lacks the set_context method."""
    # Create a mock workspace without the method
    workspace_without_method = MagicMock(spec=BaseAgentWorkspace)
    del workspace_without_method.set_context
    agent_context.state.workspace = workspace_without_method

    with caplog.at_level(logging.WARNING):
        success = await workspace_init_step.execute(agent_context, mock_status_manager)
    
    assert success is True
    assert "does not have a 'set_context' method" in caplog.text

@pytest.mark.asyncio
async def test_execute_fails_on_exception(
    workspace_init_step: WorkspaceContextInitializationStep,
    agent_context: AgentContext,
    mock_workspace: BaseAgentWorkspace,
    mock_status_manager,
    caplog
):
    """Tests that the step fails if set_context raises an exception."""
    exception_message = "Workspace connection failed"
    mock_workspace.set_context.side_effect = RuntimeError(exception_message)
    agent_context.state.workspace = mock_workspace
    
    with caplog.at_level(logging.ERROR):
        success = await workspace_init_step.execute(agent_context, mock_status_manager)

    assert success is False
    assert f"Critical failure during WorkspaceContextInitializationStep: {exception_message}" in caplog.text
