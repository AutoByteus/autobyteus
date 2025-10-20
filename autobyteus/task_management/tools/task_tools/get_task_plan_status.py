# file: autobyteus/autobyteus/task_management/tools/task_tools/get_task_plan_status.py
import json
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.task_management.converters import TaskPlanConverter

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class GetTaskPlanStatus(BaseTool):
    """A tool for agents to get a current snapshot of the team's TaskPlan."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "get_task_plan_status"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Retrieves the current status of the team's task plan, including the status of all individual tasks. "
            "Returns the status as a structured, LLM-friendly JSON string."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[None]:
        # This tool takes no arguments.
        return None

    async def _execute(self, context: 'AgentContext') -> str:
        """
        Executes the tool by fetching the task plan and using a converter to
        generate an LLM-friendly report.
        """
        logger.info(f"Agent '{context.agent_id}' is executing get_task_plan_status.")
        
        team_context: Optional['AgentTeamContext'] = context.custom_data.get("team_context")
        if not team_context:
            error_msg = "Error: Team context is not available to the agent. Cannot access the task plan."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return error_msg

        task_plan = getattr(team_context.state, 'task_plan', None)
        if not task_plan:
            error_msg = "Error: Task plan has not been initialized for this team."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return error_msg
        
        try:
            status_report_schema = TaskPlanConverter.to_schema(task_plan)
            
            if not status_report_schema:
                return "The task plan is currently empty. No tasks have been published."
            
            logger.info(f"Agent '{context.agent_id}' successfully retrieved and formatted task plan status.")
            return status_report_schema.model_dump_json(indent=2)
            
        except Exception as e:
            error_msg = f"An unexpected error occurred while retrieving or formatting task plan status: {e}"
            logger.error(f"Agent '{context.agent_id}': {error_msg}", exc_info=True)
            return error_msg
