# file: autobyteus/tests/unit_tests/tools/task_management/test_update_task_status.py
import pytest
from unittest.mock import Mock, MagicMock

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management.tools import UpdateTaskStatus
from autobyteus.task_management.base_task_board import TaskStatus
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.parameter_schema import ParameterType

TOOL_NAME = "UpdateTaskStatus"

@pytest.fixture
def tool_instance() -> UpdateTaskStatus:
    return UpdateTaskStatus()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_update_status"
    mock_context.config = Mock()
    mock_context.config.name = "TestAgent"
    mock_context.custom_data = {}
    return mock_context

@pytest.fixture
def mock_team_context() -> AgentTeamContext:
    mock_context = Mock(spec=AgentTeamContext)
    mock_state = Mock(spec=AgentTeamRuntimeState)
    mock_state.task_board = MagicMock()
    mock_context.state = mock_state
    return mock_context

def test_definition():
    """Tests the tool's definition and argument schema."""
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    assert definition.name == TOOL_NAME
    
    schema = definition.argument_schema
    assert schema is not None
    
    assert schema.get_parameter("task_id").required is True
    
    status_param = schema.get_parameter("status")
    assert status_param.required is True
    assert status_param.param_type == ParameterType.ENUM
    assert set(status_param.enum_values) == {s.value for s in TaskStatus}
    
    artifacts_param = schema.get_parameter("produced_artifact_ids")
    assert artifacts_param.required is False
    assert artifacts_param.param_type == ParameterType.ARRAY

@pytest.mark.asyncio
async def test_execute_success_no_artifacts(tool_instance: UpdateTaskStatus, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests successful status update without providing artifacts."""
    # Arrange
    mock_team_context.state.task_board.update_task_status.return_value = True
    mock_agent_context.custom_data["team_context"] = mock_team_context

    # Act
    result = await tool_instance.execute(
        mock_agent_context, 
        task_id="task-01", 
        status=TaskStatus.IN_PROGRESS.value
    )
    
    # Assert
    assert "Successfully updated status" in result
    mock_team_context.state.task_board.update_task_status.assert_called_once_with(
        "task-01", TaskStatus.IN_PROGRESS, "TestAgent", None
    )

@pytest.mark.asyncio
async def test_execute_success_with_artifacts(tool_instance: UpdateTaskStatus, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests successful completion update including produced artifact IDs."""
    # Arrange
    artifact_ids = ["art_123", "art_456"]
    mock_team_context.state.task_board.update_task_status.return_value = True
    mock_agent_context.custom_data["team_context"] = mock_team_context

    # Act
    result = await tool_instance.execute(
        mock_agent_context, 
        task_id="task-02", 
        status=TaskStatus.COMPLETED.value,
        produced_artifact_ids=artifact_ids
    )

    # Assert
    assert "Successfully updated status" in result
    assert "Linked 2 produced artifacts" in result
    mock_team_context.state.task_board.update_task_status.assert_called_once_with(
        "task-02", TaskStatus.COMPLETED, "TestAgent", artifact_ids
    )

@pytest.mark.asyncio
async def test_execute_invalid_status_string(tool_instance: UpdateTaskStatus, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests failure when an invalid status string is provided."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    
    # Act
    result = await tool_instance.execute(mock_agent_context, task_id="task-03", status="almost_done")
    
    # Assert
    assert "Error: Invalid status 'almost_done'" in result
    mock_team_context.state.task_board.update_task_status.assert_not_called()

@pytest.mark.asyncio
async def test_execute_task_board_update_fails(tool_instance: UpdateTaskStatus, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests the response when the task board returns False (e.g., task not found)."""
    # Arrange
    mock_team_context.state.task_board.update_task_status.return_value = False
    mock_agent_context.custom_data["team_context"] = mock_team_context
    
    # Act
    result = await tool_instance.execute(mock_agent_context, task_id="task-99", status=TaskStatus.FAILED.value)
    
    # Assert
    assert "Error: Failed to update status for task 'task-99'" in result
