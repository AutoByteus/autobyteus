# file: autobyteus/autobyteus/task_management/tools/publish_task_plan.py
import json
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.task_management.schemas import TaskPlanDefinitionSchema
from autobyteus.task_management.converters import TaskPlanConverter, TaskBoardConverter

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class PublishTaskPlan(BaseTool):
    """A tool for the coordinator to parse and load a generated plan into the TaskBoard."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "PublishTaskPlan"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Parses a structured object representing a complete task plan, converts it into a "
            "system-ready format, and loads it onto the team's shared task board. "
            "This action resets the task board with the new plan. Upon success, it returns "
            "the initial status of the newly loaded task board. "
            "This tool should typically only be used by the team coordinator."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        
        # Convert the Pydantic model to our native ParameterSchema for the nested object
        plan_object_schema = pydantic_to_parameter_schema(TaskPlanDefinitionSchema)
        
        schema.add_parameter(ParameterDefinition(
            name="plan",
            param_type=ParameterType.OBJECT,
            description=(
                "A structured object representing a complete task plan. This object defines the overall goal "
                "and a list of tasks with their assignees, descriptions, and dependencies. "
                "Each task must have a unique name within the plan."
            ),
            required=True,
            object_schema=plan_object_schema
        ))
        return schema

    async def _execute(self, context: 'AgentContext', plan: Dict[str, Any]) -> str:
        """
        Executes the tool by validating the plan object, using a converter to create a TaskPlan,
        and loading it onto the task board.
        """
        logger.info(f"Agent '{context.agent_id}' is executing PublishTaskPlan.")
        
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
            plan_definition_schema = TaskPlanDefinitionSchema(**plan)
            final_plan = TaskPlanConverter.from_schema(plan_definition_schema)
        except (ValidationError, ValueError) as e:
            error_msg = f"Invalid or inconsistent task plan provided: {e}"
            logger.warning(f"Agent '{context.agent_id}' provided an invalid plan for PublishTaskPlan: {error_msg}")
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"An unexpected error occurred during plan parsing or conversion: {e}"
            logger.error(f"Agent '{context.agent_id}': {error_msg}", exc_info=True)
            return f"Error: {error_msg}"

        if task_board.load_task_plan(final_plan):
            logger.info(f"Agent '{context.agent_id}': Task plan published successfully. Returning new board status.")
            status_report_schema = TaskBoardConverter.to_schema(task_board)
            if status_report_schema:
                return status_report_schema.model_dump_json(indent=2)
            else:
                return "Task plan published successfully, but could not generate status report."
        else:
            error_msg = "Failed to load task plan onto the board. This can happen if the board implementation rejects the plan."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return f"Error: {error_msg}"
