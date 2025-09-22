# file: autobyteus/autobyteus/task_management/tools/get_my_tasks.py
import json
import logging
from typing import TYPE_CHECKING, Optional, List

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.task_management.schemas import TaskDefinitionSchema
from autobyteus.task_management.base_task_board import TaskStatus

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class GetMyTasks(BaseTool):
    """A tool for an agent to inspect its own assigned tasks from the central TaskBoard."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "GetMyTasks"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Retrieves the list of tasks currently assigned to you from the team's shared task board. "
            "This is your personal to-do list. Use this to understand your current workload and decide what to do next."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[None]:
        # This tool takes no arguments.
        return None

    async def _execute(self, context: 'AgentContext') -> str:
        """
        Executes the tool by fetching tasks from the team's TaskBoard and
        filtering them for the current agent.
        """
        agent_name = context.config.name
        logger.info(f"Agent '{agent_name}' is executing GetMyTasks.")

        team_context: Optional['AgentTeamContext'] = context.custom_data.get("team_context")
        if not team_context:
            error_msg = "Error: Team context is not available. Cannot access the task board."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return error_msg

        task_board = getattr(team_context.state, 'task_board', None)
        if not task_board:
            error_msg = "Error: Task board has not been initialized for this team."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return error_msg
        
        # Filter the tasks from the central board for this agent.
        # An agent should only see tasks that are specifically for them and are ready to be worked on.
        my_tasks = [
            task for task in task_board.tasks 
            if task.assignee_name == agent_name and task_board.task_statuses.get(task.task_id) == TaskStatus.QUEUED
        ]

        if not my_tasks:
            return "Your personal task queue is empty. You have no new tasks assigned and ready to be started."

        try:
            # Convert the internal Task objects back to the LLM-friendly schema.
            tasks_for_llm = [
                TaskDefinitionSchema.model_validate(task).model_dump() for task in my_tasks
            ]
            
            logger.info(f"Agent '{agent_name}' retrieved {len(tasks_for_llm)} tasks from the central task board.")
            return json.dumps(tasks_for_llm, indent=2)
            
        except Exception as e:
            error_msg = f"An unexpected error occurred while formatting your tasks: {e}"
            logger.error(f"Agent '{agent_name}': {error_msg}", exc_info=True)
            return f"Error: {error_msg}"
