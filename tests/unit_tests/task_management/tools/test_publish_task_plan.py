# file: autobyteus/tests/unit_tests/task_management/tools/test_publish_task_plan.py
import json
import pytest
from unittest.mock import Mock, MagicMock, patch, call
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
from autobyteus.tools.usage.parsers import DefaultXmlToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse

TOOL_NAME = "PublishTaskPlan"

@pytest.fixture
def tool_instance() -> PublishTaskPlan:
    return PublishTaskPlan()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_publish_plan"
    mock_context.config = Mock() # Add config mock for execute()
    mock_context.config.name = "test_agent"
    mock_context.custom_data = {}
    return mock_context

@pytest.fixture
def mock_team_context() -> AgentTeamContext:
    mock_context = Mock(spec=AgentTeamContext)
    mock_state = Mock(spec=AgentTeamRuntimeState)
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
    Tests that get_argument_schema runs and produces a valid, nested ParameterSchema.
    """
    schema = PublishTaskPlan.get_argument_schema()

    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 1

    plan_param = schema.get_parameter("plan")
    assert plan_param is not None
    assert plan_param.name == "plan"
    assert plan_param.param_type == ParameterType.OBJECT
    assert plan_param.required is True
    
    assert isinstance(plan_param.object_schema, ParameterSchema)
    assert plan_param.object_schema is not None

    nested_schema = plan_param.object_schema
    assert len(nested_schema.parameters) == 2
    assert nested_schema.get_parameter("overall_goal") is not None
    assert nested_schema.get_parameter("tasks") is not None
    assert nested_schema.get_parameter("tasks").param_type == ParameterType.ARRAY

@pytest.mark.asyncio
@patch('autobyteus.task_management.tools.publish_task_plan.TaskBoardConverter.to_schema')
async def test_execute_with_input_from_xml_parser(mock_to_schema: MagicMock, tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """
    An integration test to verify the tool correctly processes input
    that has been parsed from a nested XML string.
    """
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    mock_team_context.state.task_board.load_task_plan.return_value = True
    mock_report = TaskStatusReportSchema(overall_goal="Launch new feature", tasks=[])
    mock_to_schema.return_value = mock_report

    xml_tool_call = """
    <tool name="PublishTaskPlan">
        <arguments>
            <arg name="plan">
                <arg name="overall_goal">Launch new feature</arg>
                <arg name="tasks">
                    <item>
                        <arg name="task_name">Design UI</arg>
                        <arg name="assignee_name">UI/UX Team</arg>
                        <arg name="description">Create mockups</arg>
                        <arg name="dependencies"></arg>
                    </item>
                    <item>
                        <arg name="task_name">Implement Backend</arg>
                        <arg name="assignee_name">Backend Team</arg>
                        <arg name="description">Setup database</arg>
                        <arg name="dependencies">
                            <item>Design UI</item>
                        </arg>
                    </item>
                </arg>
            </arg>
        </arguments>
    </tool>
    """
    # 1. Simulate the parser's output
    parser = DefaultXmlToolUsageParser()
    invocations = parser.parse(CompleteResponse(content=xml_tool_call))
    assert len(invocations) == 1
    parsed_arguments = invocations[0].arguments

    # 2. Act: Call the public execute method, which handles type coercion
    result = await tool_instance.execute(mock_agent_context, **parsed_arguments)

    # 3. Assert: Verify the TaskBoard received a correctly deserialized TaskPlan object
    mock_team_context.state.task_board.load_task_plan.assert_called_once()
    
    # Inspect the object that was passed to the mock
    call_args, _ = mock_team_context.state.task_board.load_task_plan.call_args
    loaded_plan: TaskPlan = call_args[0]

    assert isinstance(loaded_plan, TaskPlan)
    assert loaded_plan.overall_goal == "Launch new feature"
    assert len(loaded_plan.tasks) == 2
    
    task1 = loaded_plan.tasks[0]
    task2 = loaded_plan.tasks[1]
    assert task1.task_name == "Design UI"
    assert task2.assignee_name == "Backend Team"
    
    # Verify dependency hydration (name -> id)
    assert task2.dependencies == [task1.task_id]

@pytest.mark.asyncio
async def test_execute_invalid_plan_structure(tool_instance: PublishTaskPlan, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests that the tool handles a malformed plan object gracefully."""
    mock_agent_context.custom_data["team_context"] = mock_team_context
    invalid_plan_dict = {"overall_goal": "valid goal", "tasks": "this should be a list"}

    result = await tool_instance._execute(mock_agent_context, plan=invalid_plan_dict)
    assert "Error: Invalid or inconsistent task plan provided" in result
