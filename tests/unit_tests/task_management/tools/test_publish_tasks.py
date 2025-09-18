# file: autobyteus/tests/unit_tests/task_management/tools/test_publish_tasks.py
import pytest
from unittest.mock import Mock, MagicMock

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management import InMemoryTaskBoard, Task
from autobyteus.task_management.schemas import TasksDefinitionSchema, TaskDefinitionSchema
from autobyteus.task_management.tools import PublishTasks
from autobyteus.tools.parameter_schema import ParameterType

@pytest.fixture
def tool() -> PublishTasks:
    """Provides a fresh instance of the PublishTasks tool."""
    return PublishTasks()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    """Provides a mock AgentContext."""
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_publish_tasks"
    mock_context.config = Mock(name="test_agent")
    mock_context.custom_data = {}
    return mock_context

@pytest.fixture
def mock_team_context_with_board() -> AgentTeamContext:
    """Provides a mock AgentTeamContext with a MagicMock for the task board."""
    mock_context = Mock(spec=AgentTeamContext)
    mock_state = Mock(spec=AgentTeamRuntimeState)
    mock_state.task_board = MagicMock(spec=InMemoryTaskBoard)
    mock_context.state = mock_state
    return mock_context

def test_get_name(tool: PublishTasks):
    assert tool.get_name() == "PublishTasks"

def test_get_description(tool: PublishTasks):
    assert "Adds a list of new tasks" in tool.get_description()

def test_get_argument_schema(tool: PublishTasks):
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
async def test_execute_success(tool: PublishTasks, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests successful execution of the tool."""
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    task_board_mock = mock_team_context_with_board.state.task_board
    task_board_mock.add_tasks.return_value = True

    tasks_def = TasksDefinitionSchema(tasks=[
        TaskDefinitionSchema(task_name="task1", assignee_name="dev", description="d1"),
        TaskDefinitionSchema(task_name="task2", assignee_name="qa", description="d2"),
    ])
    
    result = await tool._execute(mock_agent_context, tasks=tasks_def.model_dump())

    assert result == "Successfully published 2 new task(s) to the task board."
    task_board_mock.add_tasks.assert_called_once()
    
    call_args, _ = task_board_mock.add_tasks.call_args
    added_tasks: list[Task] = call_args[0]
    assert isinstance(added_tasks, list)
    assert len(added_tasks) == 2
    assert all(isinstance(t, Task) for t in added_tasks)
    assert added_tasks[0].task_name == "task1"
    assert added_tasks[1].assignee_name == "qa"

@pytest.mark.asyncio
async def test_execute_no_team_context(tool: PublishTasks, mock_agent_context: AgentContext):
    """Tests failure when team context is missing."""
    result = await tool._execute(mock_agent_context, tasks={})
    assert "Error: Team context is not available." in result

@pytest.mark.asyncio
async def test_execute_no_task_board(tool: PublishTasks, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests failure when the task board is not initialized."""
    mock_team_context_with_board.state.task_board = None
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    result = await tool._execute(mock_agent_context, tasks={})
    assert "Error: Task board has not been initialized" in result

@pytest.mark.asyncio
async def test_execute_invalid_task_definitions(tool: PublishTasks, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests failure when provided arguments don't match the schema."""
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    
    invalid_tasks_dict = {
        "tasks": [{"task_name": "task1"}] # Task is missing required fields
    }
    
    result = await tool._execute(mock_agent_context, tasks=invalid_tasks_dict)
    assert "Error: Invalid task definitions provided" in result
    mock_team_context_with_board.state.task_board.add_tasks.assert_not_called()

@pytest.mark.asyncio
async def test_execute_duplicate_task_names(tool: PublishTasks, mock_agent_context: AgentContext, mock_team_context_with_board: AgentTeamContext):
    """Tests that the validator for unique task names is triggered."""
    mock_agent_context.custom_data["team_context"] = mock_team_context_with_board
    
    tasks_with_duplicates = {
        "tasks": [
            {"task_name": "duplicate", "assignee_name": "a1", "description": "d1"},
            {"task_name": "duplicate", "assignee_name": "a2", "description": "d2"},
        ]
    }
    
    result = await tool._execute(mock_agent_context, tasks=tasks_with_duplicates)
    assert "Error: Invalid task definitions provided" in result
    assert "Duplicate task_name 'duplicate' found" in result
