# file: autobyteus/tests/unit_tests/task_management/tools/test_get_task_board_status.py
import json
import pytest
from unittest.mock import Mock, MagicMock, patch

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management.tools import GetTaskBoardStatus
from autobyteus.task_management import InMemoryTaskBoard
from autobyteus.task_management.schemas import TaskStatusReportSchema

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
    
    # Mock the converter's return value
    mock_report = TaskStatusReportSchema(overall_goal="mock goal", tasks=[])
    mock_to_schema.return_value = mock_report
    
    # Act
    result = await tool_instance._execute(mock_agent_context)
    
    # Assert
    mock_to_schema.assert_called_once_with(mock_team_context_with_board.state.task_board)
    
    result_data = json.loads(result)
    assert result_data["overall_goal"] == "mock goal"

@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.get_task_board_status.TaskBoardConverter.to_schema')
async def test_execute_with_no_plan_loaded(mock_to_schema: MagicMock, tool_instance: GetTaskBoardStatus, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests execution when the converter returns None (i.e., no plan is loaded)."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    mock_to_schema.return_value = None

    # Act
    result = await tool_instance._execute(mock_agent_context)

    # Assert
    assert result == "The task board is currently empty. No plan has been published."

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
