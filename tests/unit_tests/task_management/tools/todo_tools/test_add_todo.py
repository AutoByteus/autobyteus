# file: autobyteus/tests/unit_tests/task_management/tools/todo_tools/test_add_todo.py
import pytest
from unittest.mock import Mock

from autobyteus.agent.context import AgentContext, AgentRuntimeState
from autobyteus.task_management.todo_list import ToDoList
from autobyteus.task_management.tools import AddToDo
from autobyteus.task_management.schemas.todo_definition import ToDoDefinitionSchema


@pytest.fixture
def tool() -> AddToDo:
    return AddToDo()


def build_context(agent_id: str = "agent_add_todo", with_list: bool = True) -> AgentContext:
    context = Mock(spec=AgentContext)
    context.agent_id = agent_id
    context.custom_data = {}
    context.status_manager = Mock()
    context.status_manager.notifier = Mock()

    state = Mock(spec=AgentRuntimeState)
    state.todo_list = ToDoList(agent_id=agent_id) if with_list else None
    context.state = state
    return context


def test_get_name(tool: AddToDo):
    assert tool.get_name() == "add_todo"


def test_get_description(tool: AddToDo):
    assert "Adds a single new item" in tool.get_description()


@pytest.mark.asyncio
async def test_execute_success(tool: AddToDo):
    context = build_context()
    todo_def = ToDoDefinitionSchema(description="Draft introduction")

    result = await tool._execute(context, **todo_def.model_dump())

    assert result == "Successfully added new item to your to-do list: 'Draft introduction' (ID: todo_0001)."
    todos = context.state.todo_list.get_all_todos()
    assert len(todos) == 1
    assert todos[0].description == "Draft introduction"
    assert todos[0].todo_id == "todo_0001"


@pytest.mark.asyncio
async def test_execute_creates_list_if_missing(tool: AddToDo):
    context = build_context(with_list=False)
    todo_def = ToDoDefinitionSchema(description="Set up environment")

    result = await tool._execute(context, **todo_def.model_dump())

    assert result == "Successfully added new item to your to-do list: 'Set up environment' (ID: todo_0001)."
    assert isinstance(context.state.todo_list, ToDoList)
    todos = context.state.todo_list.get_all_todos()
    assert len(todos) == 1
    assert todos[0].description == "Set up environment"
    assert todos[0].todo_id == "todo_0001"


@pytest.mark.asyncio
async def test_execute_invalid_payload(tool: AddToDo):
    context = build_context()
    todos_before = list(context.state.todo_list.get_all_todos())

    result = await tool._execute(context, invalid="data")

    assert result.startswith("Error: Invalid to-do item definition provided")
    assert context.state.todo_list.get_all_todos() == todos_before
