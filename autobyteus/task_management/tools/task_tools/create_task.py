# file: autobyteus/autobyteus/task_management/tools/task_tools/create_task.py
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas import TaskDefinitionSchema

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class CreateTask(BaseTool):
    """A tool for any agent to add a single new task to the team's task plan."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "create_task"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Adds a single new task to the team's shared task plan. This is an additive action "
            "and does not affect existing tasks. Use this to create follow-up tasks or delegate new work."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        # The schema for this tool is effectively the schema of a single task definition.
        return pydantic_to_parameter_schema(TaskDefinitionSchema)

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> str:
        """
        Executes the tool by validating the task definition and adding it to the plan.
        """
        agent_name = context.config.name
        task_name = kwargs.get("task_name", "unnamed task")
        logger.info(f"Agent '{agent_name}' is executing create_task for task '{task_name}'.")

        team_context: Optional['AgentTeamContext'] = context.custom_data.get("team_context")
        if not team_context:
            error_msg = "Error: Team context is not available. Cannot access the task plan."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return error_msg

        task_plan = getattr(team_context.state, 'task_plan', None)
        if not task_plan:
            error_msg = "Error: Task plan has not been initialized for this team."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return error_msg
            
        try:
            task_def_schema = TaskDefinitionSchema(**kwargs)
        except (ValidationError, ValueError) as e:
            error_msg = f"Invalid task definition provided: {e}"
            logger.warning(f"Agent '{agent_name}' provided an invalid definition for create_task: {error_msg}")
            return f"Error: {error_msg}"

        new_task = task_plan.add_task(task_def_schema)
        if new_task:
            success_msg = f"Successfully created new task '{new_task.task_name}' (ID: {new_task.task_id}) in the task plan."
            logger.info(f"Agent '{agent_name}': {success_msg}")
            return success_msg
        else:
            error_msg = f"Failed to create task '{task_name}' in the plan for an unknown reason."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return f"Error: {error_msg}"
