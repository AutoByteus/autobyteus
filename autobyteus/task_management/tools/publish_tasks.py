# file: autobyteus/autobyteus/task_management/tools/publish_tasks.py
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas import TasksDefinitionSchema
from autobyteus.task_management.task import Task

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class PublishTasks(BaseTool):
    """
    A tool to publish multiple tasks to the task board. This is an additive-only operation.
    """

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "PublishTasks"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Adds a list of new tasks to the team's shared task board. This action is additive and "
            "does not affect existing tasks or the team's overall goal."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        return pydantic_to_parameter_schema(TasksDefinitionSchema)

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> str:
        agent_name = context.config.name
        logger.info(f"Agent '{agent_name}' is executing PublishTasks.")
        
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
            
        try:
            tasks_def_schema = TasksDefinitionSchema(**kwargs)
            final_tasks = [Task(**task_def.model_dump()) for task_def in tasks_def_schema.tasks]
        except (ValidationError, ValueError) as e:
            error_msg = f"Invalid task definitions provided: {e}"
            logger.warning(f"Agent '{agent_name}' provided an invalid definition for PublishTasks: {error_msg}")
            return f"Error: {error_msg}"

        if task_board.add_tasks(tasks=final_tasks):
            success_msg = f"Successfully published {len(final_tasks)} new task(s) to the task board."
            logger.info(f"Agent '{agent_name}': {success_msg}")
            return success_msg
        else:
            # This path is less likely now but kept for robustness.
            error_msg = "Failed to publish tasks to the board for an unknown reason."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return f"Error: {error_msg}"
