# file: autobyteus/tests/unit_tests/agent/shutdown_steps/test_mcp_server_cleanup_step.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.shutdown_steps.mcp_server_cleanup_step import McpServerCleanupStep
from autobyteus.agent.context import AgentContext
from autobyteus.tools.mcp.server_instance_manager import McpServerInstanceManager

@pytest.fixture
def mcp_cleanup_step():
    """Provides a clean instance of McpServerCleanupStep."""
    return McpServerCleanupStep()

@pytest.fixture
def mock_instance_manager():
    """Provides a mock McpServerInstanceManager for patching."""
    manager_instance = MagicMock(spec=McpServerInstanceManager)
    manager_instance.cleanup_mcp_server_instances_for_agent = AsyncMock()
    return manager_instance

@pytest.mark.asyncio
@patch('autobyteus.agent.shutdown_steps.mcp_server_cleanup_step.McpServerInstanceManager')
async def test_execute_success(mock_manager_class, mcp_cleanup_step: McpServerCleanupStep, agent_context: AgentContext):
    """Tests the successful execution path."""
    mock_manager_instance = AsyncMock(spec=McpServerInstanceManager)
    mock_manager_class.return_value = mock_manager_instance

    # Re-instantiate the step to ensure it gets the patched singleton instance
    step = McpServerCleanupStep()
    success = await step.execute(agent_context)

    assert success is True
    mock_manager_instance.cleanup_mcp_server_instances_for_agent.assert_awaited_once_with(agent_context.agent_id)

@pytest.mark.asyncio
@patch('autobyteus.agent.shutdown_steps.mcp_server_cleanup_step.McpServerInstanceManager')
async def test_execute_failure(mock_manager_class, agent_context: AgentContext, caplog):
    """Tests the failure path when the instance manager raises an exception."""
    exception_message = "Failed to close server process"
    mock_manager_instance = AsyncMock(spec=McpServerInstanceManager)
    mock_manager_instance.cleanup_mcp_server_instances_for_agent.side_effect = RuntimeError(exception_message)
    mock_manager_class.return_value = mock_manager_instance

    # Re-instantiate the step to ensure it gets the patched singleton instance
    step = McpServerCleanupStep()
    with caplog.at_level(logging.ERROR):
        success = await step.execute(agent_context)

    assert success is False
    assert f"Critical failure during McpServerCleanupStep: {exception_message}" in caplog.text
    mock_manager_instance.cleanup_mcp_server_instances_for_agent.assert_awaited_once_with(agent_context.agent_id)
