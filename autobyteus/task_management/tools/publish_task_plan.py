# file: autobyteus/autobyteus/task_management/tools/publish_task_plan.py
import json
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.task_management.schemas import TaskPlanDefinition, TaskDefinition
from autobyteus.task_management.converters import TaskPlanConverter

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
            "Parses a JSON string representing a complete task plan, converts it into a "
            "system-ready format, and loads it onto the team's shared task board. "
            "This action resets the task board with the new plan. "
            "This tool should typically only be used by the team coordinator."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        plan_definition_schema = TaskPlanDefinition.model_json_schema()
        
        dummy_plan_definition = TaskPlanDefinition(
            overall_goal="Develop a web scraper to gather product data from an e-commerce site.",
            tasks=[
                TaskDefinition(
                    task_name="setup_project",
                    assignee_name="SoftwareEngineer",
                    description="Set up the project structure and install necessary libraries like Playwright and Pydantic.",
                    dependencies=[]
                ),
                TaskDefinition(
                    task_name="implement_scraper",
                    assignee_name="SoftwareEngineer",
                    description="Implement the main scraper logic to navigate to product pages and extract name, price, and description.",
                    dependencies=["setup_project"]
                ),
                TaskDefinition(
                    task_name="test_scraper",
                    assignee_name="QualityAssurance",
                    description="Write and run tests to verify the scraper handles different page layouts and errors gracefully.",
                    dependencies=["implement_scraper"]
                ),
            ]
        )
        
        # Keep the schema compact to reduce prompt length and escaping.
        compact_schema = json.dumps(plan_definition_schema)
        # Make the example pretty-printed with newlines, as requested.
        pretty_example = dummy_plan_definition.model_dump_json(indent=2)

        detailed_description = (
            "A JSON string that defines a task plan. For each task, provide a unique 'task_name' and use these names to define dependencies. "
            "The JSON string must conform to the provided schema and should be well-formatted with newlines as shown in the example.\n"
            "### Schema (compacted for brevity):\n"
            f"{compact_schema}\n"
            "### Example of a valid, well-formatted JSON string:\n"
            f"'{pretty_example}'"
        )
        
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="plan_as_json",
            param_type=ParameterType.STRING,
            description=detailed_description,
            required=True
        ))
        return schema

    async def _execute(self, context: 'AgentContext', plan_as_json: str) -> str:
        """
        Executes the tool by parsing JSON, using a converter to create a TaskPlan,
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
            # Step 1: Parse the input string and validate it against the "Definition" schema.
            plan_data = json.loads(plan_as_json)
            plan_definition = TaskPlanDefinition(**plan_data)

            # Step 2: Use the dedicated converter to create the internal TaskPlan object.
            final_plan = TaskPlanConverter.from_definition(plan_definition)

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            error_msg = f"Invalid or inconsistent task plan provided: {e}"
            logger.warning(f"Agent '{context.agent_id}' provided an invalid plan for PublishTaskPlan: {error_msg}")
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"An unexpected error occurred during plan parsing or conversion: {e}"
            logger.error(f"Agent '{context.agent_id}': {error_msg}", exc_info=True)
            return f"Error: {error_msg}"

        if task_board.load_task_plan(final_plan):
            success_msg = f"Successfully loaded new task plan '{final_plan.plan_id}' onto the team's task board."
            logger.info(f"Agent '{context.agent_id}': {success_msg}")
            return success_msg
        else:
            error_msg = "Failed to load task plan onto the board. This can happen if the board implementation rejects the plan."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return f"Error: {error_msg}"
