# file: autobyteus/autobyteus/task_management/tools/todo_tools/update_todo_status.py
import logging
from typing import TYPE_CHECKING, Any

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.task_management.todo import ToDoStatus

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

class UpdateToDoStatus(BaseTool):
    """A tool for an agent to update the status of an item on its personal to-do list."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "update_todo_status"

    @classmethod
    def get_description(cls) -> str:
        return "Updates the status of a specific item on your personal to-do list."

    @classmethod
    def get_argument_schema(cls) -> Any:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="todo_id",
            param_type=ParameterType.STRING,
            description="The unique ID of the to-do item to update (e.g., 'todo_...').",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="status",
            param_type=ParameterType.ENUM,
            description=f"The new status. Must be one of: {', '.join([s.value for s in ToDoStatus])}.",
            required=True,
            enum_values=[s.value for s in ToDoStatus]
        ))
        return schema

    async def _execute(self, context: 'AgentContext', todo_id: str, status: str) -> str:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}' is executing update_todo_status for item '{todo_id}' to status '{status}'.")

        if context.state.todo_list is None:
            return "Error: You do not have a to-do list to update."
            
        todo_list = context.state.todo_list
        
        try:
            status_enum = ToDoStatus(status)
        except ValueError:
            error_msg = f"Invalid status '{status}'. Must be one of: {', '.join([s.value for s in ToDoStatus])}."
            logger.warning(f"Agent '{agent_id}' provided invalid status for update_todo_status: {status}")
            return f"Error: {error_msg}"

        if not todo_list.get_todo_by_id(todo_id):
            error_msg = f"Failed to update status. A to-do item with ID '{todo_id}' does not exist on your list."
            logger.warning(f"Agent '{agent_id}' failed to update status for non-existent to-do item '{todo_id}'.")
            return f"Error: {error_msg}"

        if todo_list.update_todo_status(todo_id, status_enum):
            # Notify about the update
            _notify_todo_update(context)
            
            success_msg = f"Successfully updated status of to-do item '{todo_id}' to '{status}'."
            logger.info(f"Agent '{agent_id}': {success_msg}")
            return success_msg
        else:
            error_msg = f"Failed to update status for item '{todo_id}'. An unexpected error occurred."
            logger.error(f"Agent '{agent_id}': {error_msg}")
            return f"Error: {error_msg}"
