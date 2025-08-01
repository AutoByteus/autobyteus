# file: autobyteus/autobyteus/workflow/context/workflow_config.py
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from autobyteus.workflow.context.workflow_node_config import WorkflowNodeConfig

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class WorkflowConfig:
    """
    Represents the complete, static configuration for an AgenticWorkflow instance.
    This is the user's primary input for defining a workflow.
    """
    name: str
    description: str
    nodes: Tuple[WorkflowNodeConfig, ...]
    coordinator_node: WorkflowNodeConfig
    role: Optional[str] = None

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("The 'name' in WorkflowConfig must be a non-empty string.")
        if not self.nodes:
            raise ValueError("The 'nodes' collection in WorkflowConfig cannot be empty.")
        if self.coordinator_node not in self.nodes:
            raise ValueError("The 'coordinator_node' must be one of the nodes in the 'nodes' collection.")
        logger.debug(f"WorkflowConfig validated for workflow: '{self.name}'.")

