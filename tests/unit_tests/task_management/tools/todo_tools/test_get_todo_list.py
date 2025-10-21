# file: autobyteus/tests/unit_tests/task_management/tools/todo_tools/test_get_todo_list.py
import json
import pytest
from unittest.mock import Mock

from autobyteus.agent.context import AgentContext, AgentRuntimeState
from autobyteus.task_management.schemas import ToDoDefinitionSchema
from autobyteus.task_management.todo_list import ToDoList
from autobyteus.task_management.tools import GetToDoList


@pytest.fixture
def tool() -> GetToDoList:
    return GetToDoList()


def build_context(agent_id: str = "agent_get_todos", with_items: bool = True) -> AgentContext:
    context = Mock(spec=AgentContext)
    context.agent_id = agent_id

    state = Mock(spec=AgentRuntimeState)
    todo_list = ToDoList(agent_id=agent_id)
    
    if with_items:
        todo_list.add_todos(
            [
                ToDoDefinitionSchema(description="Outline proposal"),
                ToDoDefinitionSchema(description="Share proposal with mentor"),
            ]
        )
        state.todo_list = todo_list
    else:
        # For the empty case, we test both an empty list and a missing list
        state.todo_list = None
    
    context.state = state
    return context


def test_get_name(tool: GetToDoList):
    assert tool.get_name() == "get_todo_list"


def test_get_description(tool: GetToDoList):
    assert "Retrieves your current personal to-do list" in tool.get_description()


@pytest.mark.asyncio
async def test_execute_with_items(tool: GetToDoList):
    context = build_context()

    result = await tool._execute(context)

    items = json.loads(result)
    assert len(items) == 2
    
    assert items[0]['description'] == "Outline proposal"
    assert items[0]['todo_id'] == "todo_0001"
    
    assert items[1]['description'] == "Share proposal with mentor"
    assert items[1]['todo_id'] == "todo_0002"


@pytest.mark.asyncio
async def test_execute_empty_list(tool: GetToDoList):
    context = build_context(with_items=False)

    result = await tool._execute(context)

    assert result == "Your to-do list is empty."

@pytest.mark.asyncio
async def test_execute_list_with_no_items(tool: GetToDoList):
    context = build_context(with_items=False)
    # create an empty list
    context.state.todo_list = ToDoList(agent_id="test")
    
    result = await tool._execute(context)

    assert result == "Your to-do list is empty."
