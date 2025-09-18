# file: autobyteus/autobyteus/task_management/task.py
"""
Defines the data structures for a task.
"""
import logging
import uuid
from typing import List, Any
from pydantic import BaseModel, Field, model_validator

# To avoid circular import, we use a string forward reference.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from autobyteus.task_management.deliverable import FileDeliverable

logger = logging.getLogger(__name__)

def generate_task_id():
    """Generates a unique task identifier."""
    return f"task_{uuid.uuid4().hex}"

class Task(BaseModel):
    """
    Represents a single, discrete unit of work.
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

# This is necessary for Pydantic v2 to correctly handle the recursive model
from autobyteus.task_management.deliverable import FileDeliverable
Task.model_rebuild()
