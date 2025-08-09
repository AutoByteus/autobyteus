# file: autobyteus/autobyteus/task_management/artifacts/artifact_type.py
"""
Defines the classification of an ArtifactManifest.
"""
from enum import Enum

class ArtifactType(str, Enum):
    """Enumerates the possible types of an ArtifactManifest."""
    TASK_PLAN = "task_plan"
    CODE = "code"
    DOCUMENTATION = "documentation"
    RESEARCH_NOTES = "research_notes"
    TEST_RESULTS = "test_results"
    GENERAL = "general"
    
    def __str__(self) -> str:
        return self.value
