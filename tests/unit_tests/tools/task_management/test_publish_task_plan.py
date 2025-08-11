# file: autobyteus/tests/unit_tests/tools/task_management/test_publish_task_plan.py
import json
import pytest
from unittest.mock import Mock, MagicMock, patch

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management.tools import PublishTaskPlan
from autobyteus.task_management import (
    InMemoryTaskBoard,
    TaskPlan,
    TaskPlanDefinition,
    TaskDefinition
)

TOOL_NAME = "PublishTaskPlan"

@pytest.fixture
def tool_instance() -> PublishTaskPlan:
    return PublishTaskPlan()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_publish_plan"
    mock_context.custom_data = {}
    return mock_context

@pytest.fixture
def mock_team_context() -> AgentTeamContext:
    mock_context = Mock(spec=AgentTeamContext)
    mock_state = Mock(spec=AgentTeamRuntimeState)
    # Use a MagicMock for the task board to track calls to it
    mock_state.task_board = MagicMock(spec=InMemoryTaskBoard)
    mock_context.state = mock_state
    return mock_context

@pytest.fixture
def valid_plan_json() -> str:
    """Provides a valid JSON string representing a plan definition."""
    plan_def = TaskPlanDefinition(
        overall_goal="Test plan",
        tasks=[TaskDefinition(task_name="task1", assignee_name="dev", description="desc")]
    )
    return plan_def.model_dump_json()

@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.publish_task_plan.TaskPlanConverter.from_definition')
async def test_execute_success(mock_from_definition: MagicMock, tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext, valid_plan_json: str):
    """Tests the successful orchestration of parsing, converting, and loading."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    
    # Mock the converter's return value
    mock_task_plan = Mock(spec=TaskPlan)
    mock_task_plan.plan_id = "plan_123"
    mock_from_definition.return_value = mock_task_plan
    
    # Mock the task board's return value
    mock_team_context.state.task_board.load_task_plan.return_value = True

    # Act
    result = await tool_instance.execute(mock_agent_context, plan_as_json=valid_plan_json)

    # Assert
    # 1. Verify the converter was called correctly
    mock_from_definition.assert_called_once()
    
    # 2. Verify the task board was called with the result from the converter
    mock_team_context.state.task_board.load_task_plan.assert_called_once_with(mock_task_plan)
    
    # 3. Verify the success message is returned
    assert "Successfully loaded new task plan" in result
    assert "plan_123" in result

@pytest.mark.asyncio
async def test_execute_invalid_json(tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests that the tool handles malformed JSON input gracefully."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    invalid_json = '{"overall_goal": "missing quote}'

    # Act
    result = await tool_instance.execute(mock_agent_context, plan_as_json=invalid_json)

    # Assert
    assert "Error: Invalid or inconsistent task plan provided" in result

@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.publish_task_plan.TaskPlanConverter.from_definition')
async def test_execute_conversion_fails(mock_from_definition: MagicMock, tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext, valid_plan_json: str):
    """Tests that the tool handles errors during the conversion step."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    mock_from_definition.side_effect = ValueError("Invalid dependency")

    # Act
    result = await tool_instance.execute(mock_agent_context, plan_as_json=valid_plan_json)

    # Assert
    assert "Error: Invalid or inconsistent task plan provided" in result
    assert "Invalid dependency" in result

@pytest.mark.asyncio
async def test_execute_board_loading_fails(tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext, valid_plan_json: str):
    """Tests that the tool handles the case where the task board rejects the plan."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    mock_team_context.state.task_board.load_task_plan.return_value = False

    # Act
    result = await tool_instance.execute(mock_agent_context, plan_as_json=valid_plan_json)

    # Assert
    assert "Error: Failed to load task plan onto the board" in result
