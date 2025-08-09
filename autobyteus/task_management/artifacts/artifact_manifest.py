# file: autobyteus/autobyteus/task_management/artifacts/artifact_manifest.py
"""
Defines the structured metadata for a formal unit of work.
It is a pointer to the work, not the work itself.
"""
import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from .artifact_state import ArtifactState
from .artifact_type import ArtifactType

class ArtifactManifest(BaseModel):
    """Represents the metadata for a formal unit of work produced by the team."""
    artifact_id: str = Field(..., description="Unique identifier for the artifact.")
    name: str = Field(..., description="A human-readable name for the artifact.")
    description: Optional[str] = Field(None, description="A detailed description of the artifact's purpose and content.")
    artifact_type: ArtifactType = Field(..., description="The classification of the artifact.")
    state: ArtifactState = Field(default=ArtifactState.PENDING, description="The current state of the artifact in its lifecycle.")
    creator_agent_name: str = Field(..., description="The name of the agent that created or owns this artifact.")
    file_manifest: List[str] = Field(
        default_factory=list, 
        description="A list of relative file paths within the shared TeamWorkspace that constitute this artifact."
    )
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    def mark_updated(self):
        """Updates the updated_at timestamp to the current time."""
        self.updated_at = datetime.datetime.utcnow()
