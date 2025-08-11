# file: autobyteus/tests/unit_tests/task_management/tools/test_publish_task_plan.py
import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management.tools import PublishTaskPlan
from autobyteus.task_management import InMemoryTaskBoard, TaskPlan
from autobyteus.task_management.schemas import (
    TaskPlanDefinitionSchema,
    TaskDefinitionSchema,
    TaskStatusReportSchema
)
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterType

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
def valid_plan_dict() -> Dict[str, Any]:
    """Provides a valid dictionary representing a plan definition."""
    plan_def = TaskPlanDefinitionSchema(
        overall_goal="Test plan",
        tasks=[TaskDefinitionSchema(task_name="task1", assignee_name="dev", description="desc")]
    )
    return plan_def.model_dump()

def test_get_argument_schema_generates_valid_schema():
    """
    Tests that get_argument_schema runs without errors and produces a valid
    schema for the 'plan' object parameter. This test locks in the fix for
    the previous Pydantic schema generation TypeError.
    """
    # Act
    schema = PublishTaskPlan.get_argument_schema()

    # Assert
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 1

    plan_param = schema.get_parameter("plan")
    assert plan_param is not None
    assert plan_param.name == "plan"
    assert plan_param.param_type == ParameterType.OBJECT
    assert plan_param.required is True
    
    # Assert that the object schema was generated and is a dict
    assert isinstance(plan_param.object_schema, dict)
    assert plan_param.object_schema

    # Assert the basic structure of the generated JSON schema
    assert plan_param.object_schema.get("type") == "object"
    assert "properties" in plan_param.object_schema
    assert "required" in plan_param.object_schema
    
    # Assert that the properties from TaskPlanDefinitionSchema are present
    properties = plan_param.object_schema.get("properties", {})
    assert "overall_goal" in properties
    assert "tasks" in properties
    assert properties["tasks"]["type"] == "array"

    # Assert that the schema has definitions for nested objects
    assert "$defs" in plan_param.object_schema
    assert "TaskDefinitionSchema" in plan_param.object_schema["$defs"]


@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.publish_task_plan.TaskBoardConverter.to_schema')
@patch('autobyteus.task_management.tools.publish_task_plan.TaskPlanConverter.from_schema')
async def test_execute_success(mock_from_schema: MagicMock, mock_to_schema: MagicMock, tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext, valid_plan_dict: Dict[str, Any]):
    """Tests the successful orchestration of parsing, converting, and loading."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    
    mock_task_plan = Mock(spec=TaskPlan)
    mock_task_plan.plan_id = "plan_123"
    mock_from_schema.return_value = mock_task_plan
    
    mock_team_context.state.task_board.load_task_plan.return_value = True

    mock_report = TaskStatusReportSchema(overall_goal="Test plan", tasks=[])
    mock_to_schema.return_value = mock_report

    # Act
    result = await tool_instance._execute(mock_agent_context, plan=valid_plan_dict)

    # Assert
    # 1. Verify the from_schema converter was called correctly
    mock_from_schema.assert_called_once()
    assert mock_from_schema.call_args[0][0].overall_goal == "Test plan"
    
    # 2. Verify the task board was called with the result from the converter
    mock_team_context.state.task_board.load_task_plan.assert_called_once_with(mock_task_plan)
    
    # 3. Verify the to_schema converter was called
    mock_to_schema.assert_called_once_with(mock_team_context.state.task_board)

    # 4. Verify the result is the JSON dump of the status report
    assert json.loads(result) == mock_report.model_dump()

@pytest.mark.asyncio
async def test_execute_invalid_plan_structure(tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests that the tool handles a malformed plan object gracefully."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    invalid_plan_dict = {"overall_goal": "valid goal", "tasks": "this should be a list"}

    # Act
    result = await tool_instance._execute(mock_agent_context, plan=invalid_plan_dict)

    # Assert
    assert "Error: Invalid or inconsistent task plan provided" in result

@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.publish_task_plan.TaskPlanConverter.from_schema')
async def test_execute_conversion_fails(mock_from_schema: MagicMock, tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext, valid_plan_dict: Dict[str, Any]):
    """Tests that the tool handles errors during the conversion step."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    mock_from_schema.side_effect = ValueError("Invalid dependency")

    # Act
    result = await tool_instance._execute(mock_agent_context, plan=valid_plan_dict)

    # Assert
    assert "Error: Invalid or inconsistent task plan provided" in result
    assert "Invalid dependency" in result

@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.publish_task_plan.TaskPlanConverter.from_schema')
async def test_execute_board_loading_fails(mock_from_schema: MagicMock, tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext, valid_plan_dict: Dict[str, Any]):
    """Tests that the tool handles the case where the task board rejects the plan."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    mock_team_context.state.task_board.load_task_plan.return_value = False
    mock_from_schema.return_value = Mock(spec=TaskPlan) # Converter still succeeds

    # Act
    result = await tool_instance._execute(mock_agent_context, plan=valid_plan_dict)

    # Assert
    assert "Error: Failed to load task plan onto the board" in result
