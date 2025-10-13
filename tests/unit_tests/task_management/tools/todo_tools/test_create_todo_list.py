# file: autobyteus/tests/unit_tests/task_management/tools/todo_tools/test_create_todo_list.py
import pytest
from unittest.mock import Mock

from autobyteus.agent.context import AgentContext, AgentRuntimeState
from autobyteus.task_management.todo import ToDo
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

    state = Mock(spec=AgentRuntimeState)
    state.todo_list = None
    context.state = state
    return context


def test_get_name(tool: CreateToDoList):
    assert tool.get_name() == "CreateToDoList"


def test_get_description(tool: CreateToDoList):
    assert "Creates a new personal to-do list" in tool.get_description()


@pytest.mark.asyncio
async def test_execute_success(tool: CreateToDoList, mock_agent_context: AgentContext):
    todos_def = ToDosDefinitionSchema(
        todos=[
            ToDoDefinitionSchema(description="Write project outline"),
            ToDoDefinitionSchema(description="Review outline with team"),
        ]
    )

    result = await tool._execute(mock_agent_context, **todos_def.model_dump())

    assert result == "Successfully created a new to-do list with 2 items."
    todo_list = mock_agent_context.state.todo_list
    assert isinstance(todo_list, ToDoList)
    todos = todo_list.get_all_todos()
    assert len(todos) == 2
    assert [todo.description for todo in todos] == [
        "Write project outline",
        "Review outline with team",
    ]


@pytest.mark.asyncio
async def test_execute_overwrites_existing_list(
    tool: CreateToDoList, mock_agent_context: AgentContext
):
    existing_list = ToDoList(agent_id=mock_agent_context.agent_id)
    existing_list.add_todo(ToDo(description="Old item"))
    mock_agent_context.state.todo_list = existing_list

    new_list_def = ToDosDefinitionSchema(
        todos=[
            ToDoDefinitionSchema(description="New task A"),
            ToDoDefinitionSchema(description="New task B"),
        ]
    )

    await tool._execute(mock_agent_context, **new_list_def.model_dump())

    todo_list = mock_agent_context.state.todo_list
    assert todo_list is not existing_list
    descriptions = [todo.description for todo in todo_list.get_all_todos()]
    assert descriptions == ["New task A", "New task B"]


@pytest.mark.asyncio
async def test_execute_invalid_payload(
    tool: CreateToDoList, mock_agent_context: AgentContext
):
    invalid_payload = {"todos": [{"invalid": "missing description"}]}

    result = await tool._execute(mock_agent_context, **invalid_payload)

    assert result.startswith("Error: Invalid to-do list definition provided")
    assert mock_agent_context.state.todo_list is None
