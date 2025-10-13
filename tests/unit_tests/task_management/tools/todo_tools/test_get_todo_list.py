# file: autobyteus/tests/unit_tests/task_management/tools/todo_tools/test_get_todo_list.py
import json
import pytest
from unittest.mock import Mock

from autobyteus.agent.context import AgentContext, AgentRuntimeState
from autobyteus.task_management.todo import ToDo
from autobyteus.task_management.todo_list import ToDoList
from autobyteus.task_management.tools import GetToDoList


@pytest.fixture
def tool() -> GetToDoList:
    return GetToDoList()


def build_context(agent_id: str = "agent_get_todos", with_items: bool = True) -> AgentContext:
    context = Mock(spec=AgentContext)
    context.agent_id = agent_id

    state = Mock(spec=AgentRuntimeState)
    if with_items:
        todo_list = ToDoList(agent_id=agent_id)
        todo_list.add_todos(
            [
                ToDo(description="Outline proposal"),
                ToDo(description="Share proposal with mentor"),
            ]
        )
    else:
        todo_list = ToDoList(agent_id=agent_id)
        todo_list.clear()
    state.todo_list = todo_list if with_items else None
    context.state = state
    return context


def test_get_name(tool: GetToDoList):
    assert tool.get_name() == "GetToDoList"


def test_get_description(tool: GetToDoList):
    assert "Retrieves your current personal to-do list" in tool.get_description()


@pytest.mark.asyncio
async def test_execute_with_items(tool: GetToDoList):
    context = build_context()

    result = await tool._execute(context)

    items = json.loads(result)
    assert len(items) == 2
    descriptions = [item["description"] for item in items]
    assert descriptions == ["Outline proposal", "Share proposal with mentor"]


@pytest.mark.asyncio
async def test_execute_empty_list(tool: GetToDoList):
    context = build_context(with_items=False)

    result = await tool._execute(context)

    assert result == "Your to-do list is empty."
