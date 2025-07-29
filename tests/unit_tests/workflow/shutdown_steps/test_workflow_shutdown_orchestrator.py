# file: autobyteus/tests/unit_tests/workflow/shutdown_steps/test_workflow_shutdown_orchestrator.py
import pytest
import logging
from unittest.mock import AsyncMock, patch

from autobyteus.workflow.shutdown_steps.workflow_shutdown_orchestrator import WorkflowShutdownOrchestrator
from autobyteus.workflow.shutdown_steps.base_workflow_shutdown_step import BaseWorkflowShutdownStep
from autobyteus.workflow.context import WorkflowContext

# Define dummy classes for spec'ing mocks
class MockWorkflowShutdownStep1(BaseWorkflowShutdownStep):
    async def execute(self, context):
        pass

class MockWorkflowShutdownStep2(BaseWorkflowShutdownStep):
    async def execute(self, context):
        pass

@pytest.fixture
def mock_workflow_shutdown_step_1():
    step = AsyncMock(spec=MockWorkflowShutdownStep1)
    step.execute.return_value = True
    return step

@pytest.fixture
def mock_workflow_shutdown_step_2():
    step = AsyncMock(spec=MockWorkflowShutdownStep2)
    step.execute.return_value = True
    return step

def test_orchestrator_initialization_default():
    """Test that the orchestrator initializes with default steps if none are provided."""
    with patch('autobyteus.workflow.shutdown_steps.workflow_shutdown_orchestrator.AgentTeamShutdownStep') as mock_team_shutdown:
        orchestrator = WorkflowShutdownOrchestrator()
        
        assert len(orchestrator.shutdown_steps) == 1
        mock_team_shutdown.assert_called_once()

def test_orchestrator_initialization_custom(mock_workflow_shutdown_step_1, mock_workflow_shutdown_step_2):
    """Test that the orchestrator initializes with a custom list of steps."""
    custom_steps = [mock_workflow_shutdown_step_1, mock_workflow_shutdown_step_2]
    orchestrator = WorkflowShutdownOrchestrator(steps=custom_steps)
    assert orchestrator.shutdown_steps == custom_steps

@pytest.mark.asyncio
async def test_run_success(workflow_context: WorkflowContext, mock_workflow_shutdown_step_1, mock_workflow_shutdown_step_2):
    """Test a successful run where all shutdown steps pass."""
    orchestrator = WorkflowShutdownOrchestrator(steps=[mock_workflow_shutdown_step_1, mock_workflow_shutdown_step_2])
    
    success = await orchestrator.run(workflow_context)

    assert success is True
    mock_workflow_shutdown_step_1.execute.assert_awaited_once_with(workflow_context)
    mock_workflow_shutdown_step_2.execute.assert_awaited_once_with(workflow_context)

@pytest.mark.asyncio
async def test_run_fails_and_stops(workflow_context: WorkflowContext, mock_workflow_shutdown_step_1, mock_workflow_shutdown_step_2, caplog):
    """Test a failed run where one step returns False, halting the process."""
    mock_workflow_shutdown_step_1.execute.return_value = False
    
    orchestrator = WorkflowShutdownOrchestrator(steps=[mock_workflow_shutdown_step_1, mock_workflow_shutdown_step_2])
    
    with caplog.at_level(logging.ERROR):
        success = await orchestrator.run(workflow_context)

    assert success is False
    mock_workflow_shutdown_step_1.execute.assert_awaited_once_with(workflow_context)
    mock_workflow_shutdown_step_2.execute.assert_not_awaited()
    assert "Shutdown step MockWorkflowShutdownStep1 failed" in caplog.text
