# file: autobyteus/autobyteus/task_management/tools/task_tools/create_tasks.py
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas import TasksDefinitionSchema

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)


class CreateTasks(BaseTool):
    """
    A tool to create multiple tasks in the task plan. This is an additive-only operation.
    """

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "create_tasks"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Adds a list of new tasks to the team's shared task plan. This action is additive and "
            "does not affect existing tasks or the team's overall goal."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        return pydantic_to_parameter_schema(TasksDefinitionSchema)

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> str:
        agent_name = context.config.name
        logger.info(f"Agent '{agent_name}' is executing create_tasks.")
        
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
            tasks_def_schema = TasksDefinitionSchema(**kwargs)
        except (ValidationError, ValueError) as e:
            error_msg = f"Invalid task definitions provided: {e}"
            logger.warning(f"Agent '{agent_name}' provided an invalid definition for create_tasks: {error_msg}")
            return f"Error: {error_msg}"

        newly_created_tasks = task_plan.add_tasks(tasks_def_schema.tasks)
        if newly_created_tasks:
            success_msg = f"Successfully created {len(newly_created_tasks)} new task(s) in the task plan."
            logger.info(f"Agent '{agent_name}': {success_msg}")
            return success_msg
        else:
            # This case might happen if the input list was empty, or an error occurred.
            warning_msg = "No tasks were created. The provided list may have been empty."
            logger.warning(f"Agent '{agent_name}': {warning_msg}")
            return warning_msg
