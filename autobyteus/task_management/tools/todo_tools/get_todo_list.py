# file: autobyteus/autobyteus/task_management/tools/todo_tools/get_todo_list.py
import logging
import json
from typing import TYPE_CHECKING, Any

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class GetToDoList(BaseTool):
    """A tool for an agent to retrieve its own personal to-do list."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "get_todo_list"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Retrieves your current personal to-do list. "
            "Use this to see your plan, check the status of your steps, and decide what to do next."
        )

    @classmethod
    def get_argument_schema(cls) -> Any:
        return None

    async def _execute(self, context: 'AgentContext') -> str:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}' is executing get_todo_list.")

        if context.state.todo_list is None or not context.state.todo_list.get_all_todos():
            return "Your to-do list is empty."
        
        todo_list = context.state.todo_list
        
        try:
            # Convert the internal ToDo objects to a JSON-friendly list of dicts
            todos_for_llm = [
                todo.model_dump(mode='json') for todo in todo_list.get_all_todos()
            ]
            
            logger.info(f"Agent '{agent_id}' retrieved {len(todos_for_llm)} items from their to-do list.")
            return json.dumps(todos_for_llm, indent=2)
            
        except Exception as e:
            error_msg = f"An unexpected error occurred while formatting your to-do list: {e}"
            logger.error(f"Agent '{agent_id}': {error_msg}", exc_info=True)
            return f"Error: {error_msg}"
