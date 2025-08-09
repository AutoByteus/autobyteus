# file: autobyteus/autobyteus/task_management/artifacts/artifact_state.py
"""
Defines the possible lifecycle states of an ArtifactManifest.
"""
from enum import Enum

class ArtifactState(str, Enum):
    """Enumerates the possible lifecycle states of an ArtifactManifest."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

    def __str__(self) -> str:
        return self.value
