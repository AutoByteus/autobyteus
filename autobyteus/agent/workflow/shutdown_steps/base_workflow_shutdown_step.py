# file: autobyteus/autobyteus/agent/workflow/shutdown_steps/base_workflow_shutdown_step.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class BaseWorkflowShutdownStep(ABC):
    """Abstract base class for individual steps in the workflow shutdown process."""
    @abstractmethod
    async def execute(self, context: 'WorkflowContext') -> bool:
        """Executes the shutdown step."""
        raise NotImplementedError("Subclasses must implement the 'execute' method.")
