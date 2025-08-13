"""
Contains converters for translating LLM-friendly definition schemas into
internal task management objects.
"""
import logging

from autobyteus.task_management.task_plan import TaskPlan, Task
from autobyteus.task_management.schemas import TaskPlanDefinitionSchema

logger = logging.getLogger(__name__)

class TaskPlanConverter:
    """A converter to transform a TaskPlanDefinitionSchema into a system-ready TaskPlan."""

    @staticmethod
    def from_schema(plan_definition_schema: TaskPlanDefinitionSchema) -> TaskPlan:
        """
        Converts a TaskPlanDefinitionSchema object from an LLM into a fully-hydrated,
        internal TaskPlan object.

        This process involves:
        1. Converting each TaskDefinitionSchema into a system Task object (which generates a unique task_id).
        2. Assembling these Tasks into a TaskPlan (which generates a unique plan_id).
        3. Hydrating the dependencies by replacing task_name references with the newly generated task_ids.

        Args:
            plan_definition_schema: The Pydantic model representing the LLM's output.

        Returns:
            A system-ready, internally consistent TaskPlan object.
        """
        logger.debug(f"Converting TaskPlanDefinitionSchema for goal: '{plan_definition_schema.overall_goal}'")
        
        # Step 1: Convert "TaskDefinitionSchema" objects into final, internal Task objects.
        # This automatically generates the system-level 'task_id' for each.
        final_tasks = [Task(**task_def.model_dump()) for task_def in plan_definition_schema.tasks]

        # Step 2: Create the final TaskPlan object. This generates the 'plan_id'.
        final_plan = TaskPlan(
            overall_goal=plan_definition_schema.overall_goal,
            tasks=final_tasks
        )
        
        # Step 3: Hydrate dependencies: convert task_name references to system task_ids.
        final_plan.hydrate_dependencies()
        
        logger.info(f"Successfully converted TaskPlanDefinitionSchema to internal TaskPlan with ID '{final_plan.plan_id}'.")
        return final_plan
