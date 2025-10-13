# file: autobyteus/autobyteus/task_management/tools/todo_tools/create_todo_list.py
import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas.todo_definition import ToDosDefinitionSchema
from autobyteus.task_management.todo import ToDo
from autobyteus.task_management.todo_list import ToDoList

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class CreateToDoList(BaseTool):
    """A tool for an agent to create or overwrite its own personal to-do list."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "CreateToDoList"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Creates a new personal to-do list for you to manage your own sub-tasks. "
            "This will overwrite any existing to-do list you have. Use this to break down a larger task into smaller steps."
        )

    @classmethod
    def get_argument_schema(cls) -> Any:
        return pydantic_to_parameter_schema(ToDosDefinitionSchema)

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> str:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}' is executing CreateToDoList.")

        try:
            todos_def_schema = ToDosDefinitionSchema(**kwargs)
            new_todos = [ToDo(**todo_def.model_dump()) for todo_def in todos_def_schema.todos]
        except ValidationError as e:
            error_msg = f"Invalid to-do list definition provided: {e}"
            logger.warning(f"Agent '{agent_id}' provided an invalid definition for CreateToDoList: {error_msg}")
            return f"Error: {error_msg}"

        # Create a new ToDoList and add the items
        todo_list = ToDoList(agent_id=agent_id)
        todo_list.add_todos(new_todos)

        # Set it on the agent's state
        context.state.todo_list = todo_list

        success_msg = f"Successfully created a new to-do list with {len(new_todos)} items."
        logger.info(f"Agent '{agent_id}': {success_msg}")
        return success_msg
