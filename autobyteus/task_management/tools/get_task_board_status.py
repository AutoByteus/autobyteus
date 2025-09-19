# file: autobyteus/autobyteus/task_management/tools/get_task_board_status.py
import json
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.task_management.converters import TaskBoardConverter

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class GetTaskBoardStatus(BaseTool):
    """A tool for agents to get a current snapshot of the team's TaskBoard."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "GetTaskBoardStatus"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Retrieves the current status of the team's task board, including the status of all individual tasks. "
            "Returns the status as a structured, LLM-friendly JSON string."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[None]:
        # This tool takes no arguments.
        return None

    async def _execute(self, context: 'AgentContext') -> str:
        """
        Executes the tool by fetching the task board and using a converter to
        generate an LLM-friendly report.
        """
        logger.info(f"Agent '{context.agent_id}' is executing GetTaskBoardStatus.")
        
        team_context: Optional['AgentTeamContext'] = context.custom_data.get("team_context")
        if not team_context:
            error_msg = "Error: Team context is not available to the agent. Cannot access the task board."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return error_msg

        task_board = getattr(team_context.state, 'task_board', None)
        if not task_board:
            error_msg = "Error: Task board has not been initialized for this team."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return error_msg
        
        try:
            status_report_schema = TaskBoardConverter.to_schema(task_board)
            
            if not status_report_schema:
                return "The task board is currently empty. No tasks have been published."
            
            logger.info(f"Agent '{context.agent_id}' successfully retrieved and formatted task board status.")
            return status_report_schema.model_dump_json(indent=2)
            
        except Exception as e:
            error_msg = f"An unexpected error occurred while retrieving or formatting task board status: {e}"
            logger.error(f"Agent '{context.agent_id}': {error_msg}", exc_info=True)
            return error_msg
