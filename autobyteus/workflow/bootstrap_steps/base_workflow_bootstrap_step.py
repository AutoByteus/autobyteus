# file: autobyteus/autobyteus/workflow/bootstrap_steps/base_workflow_bootstrap_step.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class BaseWorkflowBootstrapStep(ABC):
    """Abstract base class for individual steps in the workflow bootstrapping process."""

    @abstractmethod
    async def execute(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        """
        Executes the bootstrap step.

        Returns:
            True if the step completed successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement the 'execute' method.")
