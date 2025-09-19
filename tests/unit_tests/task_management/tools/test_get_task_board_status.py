# file: autobyteus/tests/unit_tests/task_management/tools/test_get_task_board_status.py
import json
import pytest
from unittest.mock import Mock, MagicMock, patch

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management.tools import GetTaskBoardStatus
from autobyteus.task_management import InMemoryTaskBoard
from autobyteus.task_management.schemas import TaskStatusReportSchema, TaskStatusReportItemSchema
from autobyteus.task_management.deliverable import FileDeliverable

TOOL_NAME = "GetTaskBoardStatus"

@pytest.fixture
def tool_instance() -> GetTaskBoardStatus:
    """Provides a clean instance of the tool for each test."""
    return GetTaskBoardStatus()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    """Provides a mock AgentContext."""
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_get_status"
    mock_context.custom_data = {}
    return mock_context

@pytest.fixture
def mock_team_context_with_board() -> AgentTeamContext:
    """Provides a mock AgentTeamContext with a mocked TaskBoard."""
    mock_context = Mock(spec=AgentTeamContext)
    mock_state = Mock(spec=AgentTeamRuntimeState)
    mock_state.task_board = Mock(spec=InMemoryTaskBoard)
    mock_context.state = mock_state
    mock_context.team_id = "test_team"
    return mock_context

@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.get_task_board_status.TaskBoardConverter.to_schema')
async def test_execute_success(mock_to_schema: MagicMock, tool_instance: GetTaskBoardStatus, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests that the tool successfully calls the converter and returns its JSON output."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    
    # Mock the converter's return value without overall_goal
    mock_report = TaskStatusReportSchema(
        tasks=[TaskStatusReportItemSchema(
            task_name="task1", 
            assignee_name="a1", 
            description="d1",
            dependencies=[],
            status="not_started",
            file_deliverables=[]
        )]
    )
    mock_to_schema.return_value = mock_report
    
    # Act
    result = await tool_instance._execute(mock_agent_context)
    
    # Assert
    # The converter is now called without the overall_goal argument
    mock_to_schema.assert_called_once_with(mock_team_context_with_board.state.task_board)
    
    result_data = json.loads(result)
    assert "overall_goal" not in result_data # Verify the field is gone
    assert result_data["tasks"][0]["task_name"] == "task1"
    assert result_data["tasks"][0]["file_deliverables"] == []


@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.get_task_board_status.TaskBoardConverter.to_schema')
async def test_execute_success_with_deliverables(mock_to_schema: MagicMock, tool_instance: GetTaskBoardStatus, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests that deliverables are correctly serialized in the tool's JSON output."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    
    deliverable = FileDeliverable(
        file_path="report.pdf",
        summary="Final report",
        author_agent_name="TestAgent"
    )

    # Mock the converter's return value without overall_goal
    mock_report = TaskStatusReportSchema(
        tasks=[TaskStatusReportItemSchema(
            task_name="task1", assignee_name="a1", description="d1",
            dependencies=[], status="completed", file_deliverables=[deliverable]
        )]
    )
    mock_to_schema.return_value = mock_report
    
    # Act
    result = await tool_instance._execute(mock_agent_context)
    
    # Assert
    result_data = json.loads(result)
    assert len(result_data["tasks"][0]["file_deliverables"]) == 1
    deliverable_data = result_data["tasks"][0]["file_deliverables"][0]
    assert deliverable_data["file_path"] == "report.pdf"
    assert deliverable_data["summary"] == "Final report"
    assert "overall_goal" not in result_data


@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.get_task_board_status.TaskBoardConverter.to_schema')
async def test_execute_with_no_tasks_on_board(mock_to_schema: MagicMock, tool_instance: GetTaskBoardStatus, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests execution when the converter returns None (i.e., no tasks are on the board)."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    mock_to_schema.return_value = None

    # Act
    result = await tool_instance._execute(mock_agent_context)

    # Assert
    # The string was updated for clarity
    assert result == "The task board is currently empty. No tasks have been published."

@pytest.mark.asyncio
async def test_execute_no_team_context(tool_instance: GetTaskBoardStatus, mock_agent_context: AgentContext):
    """Tests failure when team_context is not injected into the agent's context."""
    # Act
    result = await tool_instance._execute(mock_agent_context)

    # Assert
    assert "Error: Team context is not available" in result

@pytest.mark.asyncio
async def test_execute_no_task_board(tool_instance: GetTaskBoardStatus, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests failure when the task board has not been initialized in the team's state."""
    # Arrange
    mock_team_context_with_board.state.task_board = None
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board

    # Act
    result = await tool_instance._execute(mock_agent_context)

    # Assert
    assert "Error: Task board has not been initialized" in result
