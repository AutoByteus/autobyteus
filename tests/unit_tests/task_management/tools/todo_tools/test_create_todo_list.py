# file: autobyteus/tests/unit_tests/task_management/tools/todo_tools/test_create_todo_list.py
import json
import pytest
from unittest.mock import Mock

from autobyteus.agent.context import AgentContext, AgentRuntimeState
from autobyteus.task_management.todo_list import ToDoList
from autobyteus.task_management.tools import CreateToDoList
from autobyteus.task_management.schemas.todo_definition import (
    ToDoDefinitionSchema,
    ToDosDefinitionSchema,
)


@pytest.fixture
def tool() -> CreateToDoList:
    return CreateToDoList()


@pytest.fixture
def mock_agent_context() -> AgentContext:
    context = Mock(spec=AgentContext)
    context.agent_id = "agent_create_todos"
    context.custom_data = {}
    context.status_manager = Mock()
    context.status_manager.notifier = Mock()

    state = Mock(spec=AgentRuntimeState)
    state.todo_list = None
    context.state = state
    return context


def test_get_name(tool: CreateToDoList):
    assert tool.get_name() == "create_todo_list"


def test_get_description(tool: CreateToDoList):
    assert "Creates a new personal to-do list" in tool.get_description()
    assert "Returns the full list" in tool.get_description()


@pytest.mark.asyncio
async def test_execute_success(tool: CreateToDoList, mock_agent_context: AgentContext):
    todos_def = ToDosDefinitionSchema(
        todos=[
            ToDoDefinitionSchema(description="Write project outline"),
            ToDoDefinitionSchema(description="Review outline with team"),
        ]
    )

    result = await tool._execute(mock_agent_context, **todos_def.model_dump())

    # The tool should now return a JSON string of the created items
    created_todos = json.loads(result)
    assert isinstance(created_todos, list)
    assert len(created_todos) == 2

    assert created_todos[0]["description"] == "Write project outline"
    assert created_todos[0]["todo_id"] == "todo_0001"
    assert created_todos[1]["description"] == "Review outline with team"
    assert created_todos[1]["todo_id"] == "todo_0002"

    # Also verify the state on the context
    todo_list = mock_agent_context.state.todo_list
    assert isinstance(todo_list, ToDoList)
    todos_in_state = todo_list.get_all_todos()
    assert len(todos_in_state) == 2
    assert [todo.description for todo in todos_in_state] == [
        "Write project outline",
        "Review outline with team",
    ]
    assert [todo.todo_id for todo in todos_in_state] == ["todo_0001", "todo_0002"]


@pytest.mark.asyncio
async def test_execute_overwrites_existing_list(
    tool: CreateToDoList, mock_agent_context: AgentContext
):
    # Setup: Create an existing list
    existing_list = ToDoList(agent_id=mock_agent_context.agent_id)
    existing_list.add_todos([ToDoDefinitionSchema(description="Old item")])
    mock_agent_context.state.todo_list = existing_list
    assert len(existing_list.get_all_todos()) == 1

    # Execute with a new list definition
    new_list_def = ToDosDefinitionSchema(
        todos=[
            ToDoDefinitionSchema(description="New task A"),
            ToDoDefinitionSchema(description="New task B"),
        ]
    )
    result = await tool._execute(mock_agent_context, **new_list_def.model_dump())
    json.loads(result) # Ensure it's valid json

    # Assert that the list on the context was replaced and is not the same object
    new_list_in_state = mock_agent_context.state.todo_list
    assert new_list_in_state is not existing_list

    # Assert the contents of the new list
    descriptions = [todo.description for todo in new_list_in_state.get_all_todos()]
    assert descriptions == ["New task A", "New task B"]
    ids = [todo.todo_id for todo in new_list_in_state.get_all_todos()]
    assert ids == ["todo_0001", "todo_0002"]


@pytest.mark.asyncio
async def test_execute_invalid_payload(
    tool: CreateToDoList, mock_agent_context: AgentContext
):
    invalid_payload = {"todos": [{"invalid": "missing description"}]}

    result = await tool._execute(mock_agent_context, **invalid_payload)

    assert result.startswith("Error: Invalid to-do list definition provided")
    assert mock_agent_context.state.todo_list is None
