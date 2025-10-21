# file: autobyteus/autobyteus/task_management/tools/task_tools/assign_task_to.py
import logging
from typing import TYPE_CHECKING, Optional, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas import TaskDefinitionSchema

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext
    from autobyteus.agent_team.context.team_manager import TeamManager

logger = logging.getLogger(__name__)

class AssignTaskTo(BaseTool):
    """A tool for one agent to directly create and assign a single task to another agent."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "assign_task_to"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Creates and assigns a single new task to a specific team member, and sends them a direct notification "
            "with the task details. Use this to delegate a well-defined piece of work you have identified."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        # The schema is the same as for defining a single task.
        return pydantic_to_parameter_schema(TaskDefinitionSchema)

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> str:
        """
        Executes the tool by adding the task to the central TaskPlan and then
        sending a direct message to the assignee with the task's details.
        """
        agent_name = context.config.name
        task_name = kwargs.get("task_name", "unnamed task")
        assignee_name = kwargs.get("assignee_name")
        logger.info(f"Agent '{agent_name}' is executing assign_task_to for task '{task_name}' assigned to '{assignee_name}'.")

        # --- Get Team Context and Task Plan ---
        team_context: Optional['AgentTeamContext'] = context.custom_data.get("team_context")
        if not team_context:
            error_msg = "Error: Team context is not available. Cannot access the task plan or send messages."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return error_msg

        task_plan = getattr(team_context.state, 'task_plan', None)
        if not task_plan:
            error_msg = "Error: Task plan has not been initialized for this team."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return error_msg
        
        # --- Action 1: Add the task to the Task Plan ---
        try:
            task_def_schema = TaskDefinitionSchema(**kwargs)
        except (ValidationError, ValueError) as e:
            error_msg = f"Invalid task definition provided: {e}"
            logger.warning(f"Agent '{agent_name}' provided an invalid definition for assign_task_to: {error_msg}")
            return f"Error: {error_msg}"

        # The task plan now handles ID generation and returns the created Task object.
        new_task = task_plan.add_task(task_def_schema)
        if not new_task:
            error_msg = f"Failed to publish task '{task_name}' to the plan for an unknown reason."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return f"Error: {error_msg}"
        
        logger.info(f"Agent '{agent_name}' successfully published task '{new_task.task_name}' (ID: {new_task.task_id}) to the task plan.")

        # --- Action 2: Send a direct notification message to the assignee ---
        team_manager: Optional['TeamManager'] = team_context.team_manager
        if not team_manager:
            # This is a degraded state, but the primary action (publishing) succeeded.
            warning_msg = (f"Successfully published task '{new_task.task_name}', but could not send a direct notification "
                           "because the TeamManager is not available.")
            logger.warning(f"Agent '{agent_name}': {warning_msg}")
            return warning_msg

        try:
            # Local import to break potential circular dependency at module load time.
            from autobyteus.agent_team.events.agent_team_events import InterAgentMessageRequestEvent

            notification_content = (
                f"You have been assigned a new task directly from agent '{agent_name}'.\n\n"
                f"**Task Name**: '{new_task.task_name}'\n"
                f"**Description**: {new_task.description}\n"
            )
            if new_task.dependencies:
                # Resolve dependency names for the message
                id_to_name_map = {task.task_id: task.task_name for task in task_plan.tasks}
                dep_names = [id_to_name_map.get(dep_id, str(dep_id)) for dep_id in new_task.dependencies]
                notification_content += f"**Dependencies**: {', '.join(dep_names)}\n"
            
            notification_content += "\nThis task has been logged on the team's task plan. You can begin work when its dependencies are met."

            event = InterAgentMessageRequestEvent(
                sender_agent_id=context.agent_id,
                recipient_name=new_task.assignee_name,
                content=notification_content,
                message_type="task_assignment"
            )
            
            await team_manager.dispatch_inter_agent_message_request(event)
            logger.info(f"Agent '{agent_name}' successfully dispatched a notification message for task '{new_task.task_name}' to '{new_task.assignee_name}'.")
        
        except Exception as e:
            # Again, this is a degraded state. The main goal was achieved.
            warning_msg = (f"Successfully published task '{new_task.task_name}', but failed to send the direct notification message. "
                           f"Error: {e}")
            logger.error(f"Agent '{agent_name}': {warning_msg}", exc_info=True)
            return warning_msg
            
        success_msg = f"Successfully assigned task '{new_task.task_name}' to agent '{new_task.assignee_name}' and sent a notification."
        return success_msg
