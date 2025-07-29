# file: autobyteus/autobyteus/workflow/handlers/base_workflow_event_handler.py
import logging
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class BaseWorkflowEventHandler(ABC):
    """Abstract base class for workflow event handlers."""

    @abstractmethod
    async def handle(self, event: Any, context: 'WorkflowContext') -> None:
        raise NotImplementedError("Subclasses must implement the 'handle' method.")
