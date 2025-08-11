# file: autobyteus/autobyteus/task_management/tools/update_task_status.py
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.task_management.base_task_board import TaskStatus

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class UpdateTaskStatus(BaseTool):
    """A tool for member agents to update their progress on the TaskBoard."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "UpdateTaskStatus"

    @classmethod
    def get_description(cls) -> str:
        return "Updates the status of a specific task on the team's shared task board."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="task_name",
            param_type=ParameterType.STRING,
            description="The unique name of the task to update (e.g., 'implement_scraper').",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="status",
            param_type=ParameterType.ENUM,
            description=f"The new status for the task. Must be one of: {', '.join([s.value for s in TaskStatus])}.",
            required=True,
            enum_values=[s.value for s in TaskStatus]
        ))
        return schema

    async def _execute(self, context: 'AgentContext', task_name: str, status: str) -> str:
        """
        Executes the tool to update a task's status.

        Note: This tool assumes `context.custom_data['team_context']` provides
        access to the `AgentTeamContext`.
        """
        logger.info(f"Agent '{context.agent_id}' is executing UpdateTaskStatus for task '{task_name}' to status '{status}'.")
        
        team_context: Optional['AgentTeamContext'] = context.custom_data.get("team_context")
        if not team_context:
            error_msg = "Error: Team context is not available. Cannot access the task board."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return error_msg
            
        task_board = getattr(team_context.state, 'task_board', None)
        if not task_board:
            error_msg = "Error: Task board has not been initialized for this team."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return error_msg
        
        if not task_board.current_plan:
            error_msg = "Error: No task plan is currently loaded on the task board."
            logger.warning(f"Agent '{context.agent_id}' tried to update task status, but no plan is loaded.")
            return error_msg

        # Find the task by name to get its ID
        task_id = None
        for task in task_board.current_plan.tasks:
            if task.task_name == task_name:
                task_id = task.task_id
                break

        if not task_id:
            error_msg = f"Failed to update status for task '{task_name}'. The task name does not exist on the current plan."
            logger.warning(f"Agent '{context.agent_id}' failed to update status for non-existent task '{task_name}'.")
            return f"Error: {error_msg}"
            
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            error_msg = f"Invalid status '{status}'. Must be one of: {', '.join([s.value for s in TaskStatus])}."
            logger.warning(f"Agent '{context.agent_id}' provided invalid status for UpdateTaskStatus: {status}")
            return f"Error: {error_msg}"
        
        # The agent's name is retrieved from its own context config.
        agent_name = context.config.name
        
        if task_board.update_task_status(task_id, status_enum, agent_name):
            success_msg = f"Successfully updated status of task '{task_name}' to '{status}'."
            logger.info(f"Agent '{context.agent_id}': {success_msg}")
            return success_msg
        else:
            # This path is less likely now with the pre-checks, but good to have.
            error_msg = f"Failed to update status for task '{task_name}'. An unexpected error occurred on the task board."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return f"Error: {error_msg}"
