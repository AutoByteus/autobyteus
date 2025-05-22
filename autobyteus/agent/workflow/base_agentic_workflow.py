# file: autobyteus/autobyteus/agent/workflow/base_agentic_workflow.py
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, Union

from autobyteus.agent.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.agent.group.agent_group import AgentGroup

logger = logging.getLogger(__name__)

class BaseAgenticWorkflow(ABC):
    """
    FR28: Optional abstract base class for creating domain-specific, type-safe
    APIs for agentic workflows.

    FR29: Users can subclass BaseAgenticWorkflow if they wish to create a more
    structured and specific interface for their multi-agent tasks, rather than
    using the generic `AgenticWorkflow.process(**kwargs)` method directly.

    FR30: Subclasses would typically encapsulate an `AgenticWorkflow` instance
    or an `AgentGroup` instance directly. They then define methods that map
    domain-specific inputs to the underlying workflow's execution, providing
    type safety and a clearer API for that particular workflow.
    """

    def __init__(self,
                 name: str,
                 wrapped_workflow_instance: Optional[Union[AgenticWorkflow, AgentGroup]] = None):
        """
        Initializes the BaseAgenticWorkflow.

        Args:
            name: A descriptive name for this specific workflow implementation.
            wrapped_workflow_instance: Optional. An instance of AgenticWorkflow or AgentGroup
                                       that this class will wrap and delegate to. If not provided,
                                       the subclass is responsible for initializing its own
                                       workflow/group instance.
        """
        self.name: str = name
        self._wrapped_workflow: Optional[Union[AgenticWorkflow, AgentGroup]] = wrapped_workflow_instance
        
        if self._wrapped_workflow:
            logger.info(f"BaseAgenticWorkflow '{self.name}' initialized, wrapping an instance of "
                        f"'{self._wrapped_workflow.__class__.__name__}'.")
        else:
            logger.info(f"BaseAgenticWorkflow '{self.name}' initialized without a pre-wrapped instance. "
                        "Subclass should handle workflow/group setup.")

    @property
    def wrapped_workflow(self) -> Optional[Union[AgenticWorkflow, AgentGroup]]:
        """Provides access to the wrapped AgenticWorkflow or AgentGroup instance."""
        return self._wrapped_workflow

    @abstractmethod
    async def start(self) -> None:
        """
        Starts the workflow. Subclasses should implement this to delegate
        to the start method of their wrapped AgenticWorkflow or AgentGroup.
        """
        pass

    @abstractmethod
    async def stop(self, timeout: float = 10.0) -> None:
        """
        Stops the workflow. Subclasses should implement this to delegate
        to the stop method of their wrapped AgenticWorkflow or AgentGroup.
        """
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """
        Checks if the workflow is currently running. Subclasses should implement
        this to delegate to the is_running property of their wrapped instance.
        """
        pass
    
    # Subclasses will define their own domain-specific process methods, for example:
    # @abstractmethod
    # async def generate_report(self, topic: str, length_words: int) -> Report:
    #     pass
    #
    # @abstractmethod
    # async def translate_document(self, document_path: str, target_language: str) -> TranslatedDocument:
    #     pass

    def __repr__(self) -> str:
        running_status = "N/A (not implemented by subclass)"
        try:
            running_status = str(self.is_running)
        except NotImplementedError: # pragma: no cover
            pass # Keep default N/A
            
        return (f"<{self.__class__.__name__} name='{self.name}', "
                f"wraps='{self._wrapped_workflow.__class__.__name__ if self._wrapped_workflow else 'NoneInternal'}', "
                f"is_running={running_status}>")

