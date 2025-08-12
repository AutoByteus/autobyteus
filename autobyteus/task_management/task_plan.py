# file: autobyteus/autobyteus/task_management/task_plan.py
"""
Defines the data structures for a task plan and its constituent tasks.
These models represent the static, intended structure of a plan of action.
"""
import logging
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator

# To avoid circular import, we use a string forward reference.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from autobyteus.task_management.deliverable import FileDeliverable

logger = logging.getLogger(__name__)

def generate_task_id():
    """Generates a unique task identifier."""
    return f"task_{uuid.uuid4().hex}"

def generate_plan_id():
    """Generates a unique plan identifier."""
    return f"plan_{uuid.uuid4().hex}"

class Task(BaseModel):
    """
    Represents a single, discrete unit of work within a larger TaskPlan.
    """
    task_name: str = Field(..., description="A short, unique, descriptive name for this task within the plan (e.g., 'setup_project', 'implement_scraper'). Used for defining dependencies.")
    
    task_id: str = Field(default_factory=generate_task_id, description="A unique system-generated identifier for this task within the plan.")
    
    assignee_name: str = Field(..., description="The unique name of the agent or sub-team responsible for executing this task (e.g., 'SoftwareEngineer', 'ResearchTeam').")
    description: str = Field(..., description="A clear and concise description of what this task entails.")
    
    dependencies: List[str] = Field(
        default_factory=list,
        description="A list of 'task_name' values for tasks that must be completed before this one can be started."
    )
    
    # This is the updated field as per user request.
    file_deliverables: List["FileDeliverable"] = Field(
        default_factory=list,
        description="A list of file deliverables that were produced as a result of completing this task."
    )

    @model_validator(mode='before')
    @classmethod
    def handle_local_id_compatibility(cls, data: Any) -> Any:
        """Handles backward compatibility for the 'local_id' field."""
        if isinstance(data, dict) and 'local_id' in data:
            data['task_name'] = data.pop('local_id')
        # Compatibility for old artifact field
        if isinstance(data, dict) and 'produced_artifact_ids' in data:
            del data['produced_artifact_ids']
        return data

    def model_post_init(self, __context: Any) -> None:
        """Called after the model is initialized and validated."""
        logger.debug(f"Task created: Name='{self.task_name}', SystemID='{self.task_id}', Assignee='{self.assignee_name}'")


class TaskPlan(BaseModel):
    """
    Represents a complete, static plan for achieving a high-level goal.
    It is composed of a list of interconnected tasks.
    """
    plan_id: str = Field(default_factory=generate_plan_id, description="A unique system-generated identifier for this entire plan.")
    
    overall_goal: str = Field(..., description="The high-level objective that this plan is designed to achieve.")
    tasks: List[Task] = Field(..., description="The list of tasks that make up this plan.")

    @field_validator('tasks')
    def task_names_must_be_unique(cls, tasks: List[Task]) -> List[Task]:
        """Ensures that the LLM-provided task_names are unique within the plan."""
        seen_names = set()
        for task in tasks:
            if task.task_name in seen_names:
                raise ValueError(f"Duplicate task_name '{task.task_name}' found in task list. Each task_name must be unique within the plan.")
            seen_names.add(task.task_name)
        return tasks

    def hydrate_dependencies(self) -> 'TaskPlan':
        """
        Converts the dependency list of task_names to system-generated task_ids.
        This makes the plan internally consistent and ready for execution.
        """
        name_to_system_id_map = {task.task_name: task.task_id for task in self.tasks}
        
        for task in self.tasks:
            # Create a new list for the resolved dependency IDs
            resolved_deps = []
            for dep_name in task.dependencies:
                if dep_name not in name_to_system_id_map:
                    raise ValueError(f"Task '{task.task_name}' has an invalid dependency: '{dep_name}' does not correspond to any task's name.")
                resolved_deps.append(name_to_system_id_map[dep_name])
            # Replace the old list of names with the new list of system_ids
            task.dependencies = resolved_deps
        
        logger.debug(f"TaskPlan '{self.plan_id}' successfully hydrated dependencies.")
        return self

    def model_post_init(self, __context: Any) -> None:
        """Called after the model is initialized and validated."""
        logger.debug(f"TaskPlan created: ID='{self.plan_id}', Tasks={len(self.tasks)}")

# This is necessary for Pydantic v2 to correctly handle the recursive model
from autobyteus.task_management.deliverable import FileDeliverable
Task.model_rebuild()
