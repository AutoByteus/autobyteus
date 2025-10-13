# file: autobyteus/tests/unit_tests/task_management/tools/todo_tools/test_update_todo_status.py
import pytest
from unittest.mock import Mock

from autobyteus.agent.context import AgentContext, AgentRuntimeState
from autobyteus.task_management.todo import ToDo, ToDoStatus
from autobyteus.task_management.todo_list import ToDoList
from autobyteus.task_management.tools import UpdateToDoStatus


@pytest.fixture
def tool() -> UpdateToDoStatus:
    return UpdateToDoStatus()


def build_context(agent_id: str = "agent_update_todo", with_list: bool = True) -> AgentContext:
    context = Mock(spec=AgentContext)
    context.agent_id = agent_id

    state = Mock(spec=AgentRuntimeState)
    if with_list:
        todo_list = ToDoList(agent_id=agent_id)
        todo_list.add_todo(ToDo(description="Initial step"))
    else:
        todo_list = None
    state.todo_list = todo_list
    context.state = state
    return context


def test_get_name(tool: UpdateToDoStatus):
    assert tool.get_name() == "UpdateToDoStatus"


def test_get_description(tool: UpdateToDoStatus):
    assert "Updates the status of a specific item" in tool.get_description()


@pytest.mark.asyncio
async def test_execute_success(tool: UpdateToDoStatus):
    context = build_context()
    todo = context.state.todo_list.get_all_todos()[0]

    result = await tool._execute(
        context, todo_id=todo.todo_id, status=ToDoStatus.DONE.value
    )

    assert (
        result
        == f"Successfully updated status of to-do item '{todo.todo_id}' to '{ToDoStatus.DONE.value}'."
    )
    assert todo.status == ToDoStatus.DONE


@pytest.mark.asyncio
async def test_execute_missing_list(tool: UpdateToDoStatus):
    context = build_context(with_list=False)

    result = await tool._execute(context, todo_id="missing", status=ToDoStatus.DONE.value)

    assert result == "Error: You do not have a to-do list to update."


@pytest.mark.asyncio
async def test_execute_invalid_status(tool: UpdateToDoStatus):
    context = build_context()
    todo = context.state.todo_list.get_all_todos()[0]

    result = await tool._execute(context, todo_id=todo.todo_id, status="unknown")

    assert result.startswith("Error: Invalid status 'unknown'")
    assert todo.status == ToDoStatus.PENDING


@pytest.mark.asyncio
async def test_execute_missing_todo(tool: UpdateToDoStatus):
    context = build_context()

    result = await tool._execute(
        context, todo_id="todo_nonexistent", status=ToDoStatus.IN_PROGRESS.value
    )

    assert result.startswith(
        "Error: Failed to update status. A to-do item with ID 'todo_nonexistent' does not exist"
    )
