# file: autobyteus/tests/unit_tests/task_management/tools/task_tools/test_publish_task.py
import pytest
from unittest.mock import Mock, MagicMock

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management import InMemoryTaskPlan, Task
from autobyteus.task_management.schemas import TaskDefinitionSchema
from autobyteus.task_management.tools import PublishTask
from autobyteus.utils.parameter_schema import ParameterType

@pytest.fixture
def tool() -> PublishTask:
    """Provides a fresh instance of the PublishTask tool."""
    return PublishTask()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    """Provides a mock AgentContext."""
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_publish_task"
    mock_context.config = Mock(name="test_agent")
    mock_context.custom_data = {}
    return mock_context

@pytest.fixture
def mock_team_context_with_board() -> AgentTeamContext:
    """Provides a mock AgentTeamContext with a MagicMock for the task plan."""
    mock_context = Mock(spec=AgentTeamContext)
    mock_state = Mock(spec=AgentTeamRuntimeState)
    mock_state.task_plan = MagicMock(spec=InMemoryTaskPlan)
    mock_context.state = mock_state
    return mock_context

def test_get_name(tool: PublishTask):
    assert tool.get_name() == "PublishTask"

def test_get_description(tool: PublishTask):
    assert "Adds a single new task" in tool.get_description()

def test_get_argument_schema(tool: PublishTask):
    """Ensures the schema matches the TaskDefinitionSchema."""
    schema = tool.get_argument_schema()
    assert schema is not None
    assert schema.get_parameter("task_name") is not None
    assert schema.get_parameter("assignee_name") is not None
    assert schema.get_parameter("description") is not None
    assert schema.get_parameter("dependencies") is not None
    assert schema.get_parameter("task_name").param_type == ParameterType.STRING
    assert schema.get_parameter("dependencies").param_type == ParameterType.ARRAY

@pytest.mark.asyncio
async def test_execute_success(tool: PublishTask, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests successful execution of the tool."""
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    task_plan_mock = mock_team_context_with_board.state.task_plan
    task_plan_mock.add_task.return_value = True

    task_def = TaskDefinitionSchema(
        task_name="test_task",
        assignee_name="dev_agent",
        description="A test task.",
        dependencies=["another_task"]
    )
    
    result = await tool._execute(mock_agent_context, **task_def.model_dump())

    assert result == "Successfully published new task 'test_task' to the task plan."
    task_plan_mock.add_task.assert_called_once()
    
    # Verify the object passed to add_task is a Task instance with correct data
    call_args, _ = task_plan_mock.add_task.call_args
    added_task: Task = call_args[0]
    assert isinstance(added_task, Task)
    assert added_task.task_name == "test_task"
    assert added_task.assignee_name == "dev_agent"
    assert added_task.dependencies == ["another_task"]

@pytest.mark.asyncio
async def test_execute_no_team_context(tool: PublishTask, mock_agent_context: AgentContext):
    """Tests failure when team context is missing."""
    result = await tool._execute(mock_agent_context, task_name="t", assignee_name="a", description="d")
    assert "Error: Team context is not available." in result

@pytest.mark.asyncio
async def test_execute_no_task_plan(tool: PublishTask, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests failure when the task plan is not initialized."""
    mock_team_context_with_board.state.task_plan = None
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    result = await tool._execute(mock_agent_context, task_name="t", assignee_name="a", description="d")
    assert "Error: Task plan has not been initialized" in result

@pytest.mark.asyncio
async def test_execute_invalid_task_definition(tool: PublishTask, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests failure when provided arguments don't match the schema."""
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    
    invalid_kwargs = {
        "task_name": "missing_fields_task"
        # Missing assignee_name and description
    }
    
    result = await tool._execute(mock_agent_context, **invalid_kwargs)
    assert "Error: Invalid task definition provided" in result
    mock_team_context_with_board.state.task_plan.add_task.assert_not_called()
