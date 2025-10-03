# file: autobyteus/autobyteus/task_management/tools/publish_task.py
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas import TaskDefinitionSchema
from autobyteus.task_management.task import Task

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class PublishTask(BaseTool):
    """A tool for any agent to add a single new task to the team's task board."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "PublishTask"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Adds a single new task to the team's shared task board. This is an additive action "
            "and does not affect existing tasks. Use this to create follow-up tasks or delegate new work."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        # The schema for this tool is effectively the schema of a single task definition.
        return pydantic_to_parameter_schema(TaskDefinitionSchema)

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> str:
        """
        Executes the tool by validating the task object and adding it to the board.
        """
        agent_name = context.config.name
        task_name = kwargs.get("task_name", "unnamed task")
        logger.info(f"Agent '{agent_name}' is executing PublishTask for task '{task_name}'.")

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
            task_def_schema = TaskDefinitionSchema(**kwargs)
            new_task = Task(**task_def_schema.model_dump())
        except (ValidationError, ValueError) as e:
            error_msg = f"Invalid task definition provided: {e}"
            logger.warning(f"Agent '{agent_name}' provided an invalid definition for PublishTask: {error_msg}")
            return f"Error: {error_msg}"

        if task_board.add_task(new_task):
            success_msg = f"Successfully published new task '{new_task.task_name}' to the task board."
            logger.info(f"Agent '{agent_name}': {success_msg}")
            return success_msg
        else:
            # This path is less likely now but kept for robustness.
            error_msg = "Failed to publish task to the board for an unknown reason."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return f"Error: {error_msg}"
