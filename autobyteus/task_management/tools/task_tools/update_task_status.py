import logging
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.base_task_board import TaskStatus
from autobyteus.task_management.deliverable import FileDeliverable
from autobyteus.task_management.schemas import FileDeliverableSchema

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class UpdateTaskStatus(BaseTool):
    """A tool for member agents to update their progress and submit file deliverables on the TaskBoard."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "UpdateTaskStatus"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Updates the status of a specific task on the team's shared task board. "
            "When completing a task, this tool can also be used to formally submit a list of file deliverables."
        )

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
        schema.add_parameter(ParameterDefinition(
            name="deliverables",
            param_type=ParameterType.ARRAY,
            description="Optional. A list of file deliverables to submit for this task, typically when status is 'completed'. Each deliverable must include a file_path and a summary.",
            required=False,
            array_item_schema=pydantic_to_parameter_schema(FileDeliverableSchema)
        ))
        return schema

    async def _execute(self, context: 'AgentContext', task_name: str, status: str, deliverables: Optional[List[Dict[str, Any]]] = None) -> str:
        agent_name = context.config.name
        log_msg = f"Agent '{agent_name}' is executing UpdateTaskStatus for task '{task_name}' to status '{status}'"
        if deliverables:
            log_msg += f" with {len(deliverables)} deliverable(s)."
        logger.info(log_msg)
        
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
        
        if not task_board.tasks:
            error_msg = "Error: No tasks are currently loaded on the task board."
            logger.warning(f"Agent '{agent_name}' tried to update task status, but the board is empty.")
            return error_msg

        target_task = next((t for t in task_board.tasks if t.task_name == task_name), None)

        if not target_task:
            error_msg = f"Failed to update status for task '{task_name}'. The task name does not exist on the current plan."
            logger.warning(f"Agent '{agent_name}' failed to update status for non-existent task '{task_name}'.")
            return f"Error: {error_msg}"
            
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            error_msg = f"Invalid status '{status}'. Must be one of: {', '.join([s.value for s in TaskStatus])}."
            logger.warning(f"Agent '{agent_name}' provided invalid status for UpdateTaskStatus: {status}")
            return f"Error: {error_msg}"
        
        if deliverables:
            try:
                for d_data in deliverables:
                    deliverable_schema = FileDeliverableSchema(**d_data)
                    full_deliverable = FileDeliverable(**deliverable_schema.model_dump(), author_agent_name=agent_name)
                    target_task.file_deliverables.append(full_deliverable)
                logger.info(f"Agent '{agent_name}' successfully processed and added {len(deliverables)} deliverables to task '{task_name}'.")
            except (ValidationError, TypeError) as e:
                error_msg = f"Failed to process deliverables due to invalid data: {e}. Task status was NOT updated."
                logger.warning(f"Agent '{agent_name}': {error_msg}")
                return f"Error: {error_msg}"

        if not task_board.update_task_status(target_task.task_id, status_enum, agent_name):
            error_msg = f"Failed to update status for task '{task_name}'. An unexpected error occurred on the task board."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return f"Error: {error_msg}"

        success_msg = f"Successfully updated status of task '{task_name}' to '{status}'."
        if deliverables:
            success_msg += f" and submitted {len(deliverables)} deliverable(s)."
        logger.info(f"Agent '{agent_name}': {success_msg}")
        return success_msg
