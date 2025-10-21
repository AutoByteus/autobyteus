# file: autobyteus/autobyteus/task_management/tools/todo_tools/create_todo_list.py
import json
import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas.todo_definition import ToDosDefinitionSchema
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

class CreateToDoList(BaseTool):
    """A tool for an agent to create or overwrite its own personal to-do list."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "create_todo_list"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Creates a new personal to-do list for you to manage your own sub-tasks. "
            "This will overwrite any existing to-do list you have. Use this to break down a larger task into smaller steps. "
            "Returns the full list of created to-do items with their new IDs."
        )

    @classmethod
    def get_argument_schema(cls) -> Any:
        return pydantic_to_parameter_schema(ToDosDefinitionSchema)

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> str:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}' is executing create_todo_list.")

        try:
            todos_def_schema = ToDosDefinitionSchema(**kwargs)
        except ValidationError as e:
            error_msg = f"Invalid to-do list definition provided: {e}"
            logger.warning(f"Agent '{agent_id}' provided an invalid definition for create_todo_list: {error_msg}")
            return f"Error: {error_msg}"

        # Create a new ToDoList, which overwrites any existing one.
        todo_list = ToDoList(agent_id=agent_id)
        # Add items from definitions; this now returns the created ToDo objects.
        new_todos = todo_list.add_todos(todos_def_schema.todos)

        # Set the new list on the agent's state.
        context.state.todo_list = todo_list

        # Notify any UI components about the update.
        _notify_todo_update(context)

        # Return the created list to the LLM so it knows the new IDs.
        try:
            todos_for_llm = [todo.model_dump(mode='json') for todo in new_todos]
            logger.info(f"Agent '{agent_id}' successfully created a new to-do list with {len(new_todos)} items.")
            return json.dumps(todos_for_llm, indent=2)
        except Exception as e:
            error_msg = f"An unexpected error occurred while formatting the new to-do list: {e}"
            logger.error(f"Agent '{agent_id}': {error_msg}", exc_info=True)
            # Fallback message
            return f"Successfully created {len(new_todos)} to-do items, but failed to return them in the response."
