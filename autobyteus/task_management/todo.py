# file: autobyteus/autobyteus/task_management/todo.py
"""
Defines the data structures for a ToDo item.
A ToDo represents a small, personal step an agent creates for itself to break down a larger Task.
"""
import logging
import uuid
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

def generate_todo_id():
    """Generates a unique todo identifier."""
    return f"todo_{uuid.uuid4().hex}"

class ToDoStatus(str, Enum):
    """Enumerates the possible lifecycle states of a ToDo item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class ToDo(BaseModel):
    """
    Represents a single, discrete item on a personal ToDoList.
    It is intentionally simpler than a `Task`, as it's for an agent's internal planning.
    """
    description: str = Field(..., description="A clear and concise description of what this to-do item or step entails.")
    todo_id: str = Field(default_factory=generate_todo_id, description="A unique system-generated identifier for this to-do item.")
    status: ToDoStatus = Field(default=ToDoStatus.PENDING, description="The current status of this to-do item.")

    def model_post_init(self, __context: any) -> None:
        """Called after the model is initialized and validated."""
        logger.debug(f"ToDo created: ID='{self.todo_id}', Description='{self.description}'")
