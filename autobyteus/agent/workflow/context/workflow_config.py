# file: autobyteus/autobyteus/agent/workflow/context/workflow_config.py
import logging
from dataclasses import dataclass
from typing import List

from .workflow_node_config import WorkflowNodeConfig

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class WorkflowConfig:
    """
    Represents the complete, static configuration for an AgenticWorkflow instance.
    This is the user's primary input for defining a workflow.
    """
    nodes: List[WorkflowNodeConfig]
    description: str
    coordinator_node: WorkflowNodeConfig

    def __post_init__(self):
        if not self.nodes:
            raise ValueError("The 'nodes' list in WorkflowConfig cannot be empty.")
        if self.coordinator_node not in self.nodes:
            raise ValueError("The 'coordinator_node' must be one of the nodes in the 'nodes' list.")
        logger.debug(f"WorkflowConfig validated for workflow: {self.description[:50]}...")
