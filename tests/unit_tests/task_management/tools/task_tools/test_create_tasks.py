# file: autobyteus/tests/unit_tests/task_management/tools/task_tools/test_create_tasks.py
import pytest
from unittest.mock import Mock, MagicMock

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management import InMemoryTaskPlan, Task
from autobyteus.task_management.schemas import TasksDefinitionSchema, TaskDefinitionSchema
from autobyteus.task_management.tools import CreateTasks
from autobyteus.utils.parameter_schema import ParameterType

@pytest.fixture
def tool() -> CreateTasks:
    """Provides a fresh instance of the CreateTasks tool."""
    return CreateTasks()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    """Provides a mock AgentContext."""
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_create_tasks"
    mock_context.config = Mock(name="test_agent")
    mock_context.config.name = "test_agent"
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

def test_get_name(tool: CreateTasks):
    assert tool.get_name() == "CreateTasks"

def test_get_description(tool: CreateTasks):
    assert "Adds a list of new tasks" in tool.get_description()

def test_get_argument_schema(tool: CreateTasks):
    """Ensures the schema matches the TasksDefinitionSchema."""
    schema = tool.get_argument_schema()
    assert schema is not None
    tasks_param = schema.get_parameter("tasks")
    assert tasks_param is not None
    assert tasks_param.param_type == ParameterType.ARRAY
    assert tasks_param.array_item_schema is not None
    
    # The item schema should be a ParameterSchema object
    item_schema = tasks_param.array_item_schema
    assert item_schema.get_parameter("task_name") is not None
    assert item_schema.get_parameter("assignee_name") is not None

@pytest.mark.asyncio
async def test_execute_success(tool: CreateTasks, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests successful execution of the tool."""
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    task_plan_mock = mock_team_context_with_board.state.task_plan
    # FIX: Mock add_tasks to return a list of 2 mock Task objects
    task_plan_mock.add_tasks.return_value = [Mock(spec=Task), Mock(spec=Task)]

    tasks_def = TasksDefinitionSchema(tasks=[
        TaskDefinitionSchema(task_name="task1", assignee_name="dev", description="d1"),
        TaskDefinitionSchema(task_name="task2", assignee_name="qa", description="d2"),
    ])
    
    result = await tool._execute(mock_agent_context, tasks=tasks_def.model_dump()["tasks"])

    assert result == "Successfully created 2 new task(s) in the task plan."
    task_plan_mock.add_tasks.assert_called_once()
    
    # FIX: Retrieve positional argument and check its type
    call_args, _ = task_plan_mock.add_tasks.call_args
    added_task_defs: list[TaskDefinitionSchema] = call_args[0]
    
    assert isinstance(added_task_defs, list)
    assert len(added_task_defs) == 2
    assert all(isinstance(t, TaskDefinitionSchema) for t in added_task_defs)
    assert added_task_defs[0].task_name == "task1"
    assert added_task_defs[1].assignee_name == "qa"

@pytest.mark.asyncio
async def test_execute_no_team_context(tool: CreateTasks, mock_agent_context: AgentContext):
    """Tests failure when team context is missing."""
    result = await tool._execute(mock_agent_context, tasks=[])
    assert "Error: Team context is not available." in result

@pytest.mark.asyncio
async def test_execute_no_task_plan(tool: CreateTasks, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests failure when the task plan is not initialized."""
    mock_team_context_with_board.state.task_plan = None
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    result = await tool._execute(mock_agent_context, tasks=[])
    assert "Error: Task plan has not been initialized" in result

@pytest.mark.asyncio
async def test_execute_invalid_task_definitions(tool: CreateTasks, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests failure when provided arguments don't match the schema."""
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    
    invalid_tasks_dict = {
        "tasks": [{"task_name": "task1"}] # Task is missing required fields
    }
    
    result = await tool._execute(mock_agent_context, tasks=invalid_tasks_dict["tasks"])
    assert "Error: Invalid task definitions provided" in result
    mock_team_context_with_board.state.task_plan.add_tasks.assert_not_called()

@pytest.mark.asyncio
async def test_execute_duplicate_task_names(tool: CreateTasks, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests that the validator for unique task names is triggered."""
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    
    tasks_with_duplicates = {
        "tasks": [
            {"task_name": "duplicate", "assignee_name": "a1", "description": "d1"},
            {"task_name": "duplicate", "assignee_name": "a2", "description": "d2"},
        ]
    }
    
    result = await tool._execute(mock_agent_context, tasks=tasks_with_duplicates["tasks"])
    assert "Error: Invalid task definitions provided" in result
    assert "Duplicate task_name 'duplicate' found" in result
