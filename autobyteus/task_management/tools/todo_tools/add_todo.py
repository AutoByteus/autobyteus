# file: autobyteus/autobyteus/task_management/tools/todo_tools/add_todo.py
import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas.todo_definition import ToDoDefinitionSchema
from autobyteus.task_management.todo_list import ToDoList

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

def _notify_todo_update(context: 'AgentContext'):
    if context.phase_manager and context.phase_manager.notifier:
        todo_list = context.state.todo_list
        if todo_list:
            todos_for_llm = [todo.model_dump(mode='json') for todo in todo_list.get_all_todos()]
            context.phase_manager.notifier.notify_agent_data_todo_list_updated(todos_for_llm)
            logger.debug(f"Agent '{context.agent_id}': Notified ToDo list update with {len(todos_for_llm)} items.")

class AddToDo(BaseTool):
    """A tool for an agent to add a new item to its personal to-do list."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "add_todo"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Adds a single new item to your personal to-do list. "
            "Use this if you discover a new step is needed to complete your task."
        )

    @classmethod
    def get_argument_schema(cls) -> Any:
        return pydantic_to_parameter_schema(ToDoDefinitionSchema)

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> str:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}' is executing add_todo.")

        if context.state.todo_list is None:
            # If no list exists, create one.
            context.state.todo_list = ToDoList(agent_id=agent_id)
            logger.info(f"Agent '{agent_id}': No existing to-do list found, created a new one.")
        
        todo_list = context.state.todo_list

        try:
            todo_def_schema = ToDoDefinitionSchema(**kwargs)
        except ValidationError as e:
            error_msg = f"Invalid to-do item definition provided: {e}"
            logger.warning(f"Agent '{agent_id}' provided an invalid definition for add_todo: {error_msg}")
            return f"Error: {error_msg}"

        # The add_todo method now takes the definition and returns the created ToDo object
        new_todo = todo_list.add_todo(todo_def_schema)

        if new_todo:
            # Notify about the update
            _notify_todo_update(context)

            success_msg = f"Successfully added new item to your to-do list: '{new_todo.description}' (ID: {new_todo.todo_id})."
            logger.info(f"Agent '{agent_id}': {success_msg}")
            return success_msg
        else:
            # This path is unlikely given the refactoring but kept for robustness.
            error_msg = "Failed to add item to the to-do list for an unknown reason."
            logger.error(f"Agent '{agent_id}': {error_msg}")
            return f"Error: {error_msg}"
