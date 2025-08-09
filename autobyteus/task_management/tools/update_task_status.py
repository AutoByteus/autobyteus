# file: autobyteus/autobyteus/task_management/tools/update_task_status.py
import logging
from typing import TYPE_CHECKING, Optional, List

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
        return (
            "Updates the status of a specific task on the team's shared task board. "
            "When marking a task as 'completed', this tool can also link the artifacts that were produced."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="task_id",
            param_type=ParameterType.STRING,
            description="The unique ID of the task to update.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="status",
            param_type=ParameterType.ENUM,
            description=f"The new status for the task. Must be one of: {', '.join([s.value for s in TaskStatus])}.",
            required=True,
            enum_values=[s.value for s in TaskStatus]
        ))
        # NEW: Add optional parameter for produced artifact IDs.
        schema.add_parameter(ParameterDefinition(
            name="produced_artifact_ids",
            param_type=ParameterType.ARRAY,
            description="Optional. A list of artifact IDs that were created or updated as a result of completing this task. Use this when status is 'completed'.",
            required=False,
            array_item_schema={"type": "string"}
        ))
        return schema

    async def _execute(self, context: 'AgentContext', task_id: str, status: str, produced_artifact_ids: Optional[List[str]] = None) -> str:
        """
        Executes the tool to update a task's status.

        Note: This tool assumes `context.custom_data['team_context']` provides
        access to the `AgentTeamContext`.
        """
        logger.info(f"Agent '{context.agent_id}' is executing UpdateTaskStatus for task '{task_id}' to status '{status}'.")
        
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
            
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            error_msg = f"Invalid status '{status}'. Must be one of: {', '.join([s.value for s in TaskStatus])}."
            logger.warning(f"Agent '{context.agent_id}' provided invalid status for UpdateTaskStatus: {status}")
            return f"Error: {error_msg}"
        
        # The agent's name is retrieved from its own context config.
        agent_name = context.config.name
        
        # MODIFIED: Pass the produced_artifact_ids to the task board method.
        if task_board.update_task_status(task_id, status_enum, agent_name, produced_artifact_ids):
            success_msg = f"Successfully updated status of task '{task_id}' to '{status}'."
            if produced_artifact_ids:
                success_msg += f" Linked {len(produced_artifact_ids)} produced artifacts."
            logger.info(f"Agent '{context.agent_id}': {success_msg}")
            return success_msg
        else:
            error_msg = f"Failed to update status for task '{task_id}'. The task ID may not exist on the current plan."
            logger.warning(f"Agent '{context.agent_id}' failed to update status for non-existent task '{task_id}'.")
            return f"Error: {error_msg}"
