
# file: autobyteus/autobyteus/agent/status/manager.py
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from autobyteus.agent.status.status_enum import AgentStatus

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier


logger = logging.getLogger(__name__)

class AgentStatusManager:
    """
    Handles lifecycle processor execution and external status notifications.
    Status is derived from events; this manager does not own the source of truth.
    """
    def __init__(self, context: 'AgentContext', notifier: Optional['AgentExternalEventNotifier'] = None):
        self.context: 'AgentContext' = context
        if notifier is None:
            raise ValueError("AgentStatusManager requires a notifier.")
        self.notifier = notifier
        if not isinstance(self.context.current_status, AgentStatus):
            self.context.current_status = AgentStatus.UNINITIALIZED

        logger.debug(
            f"AgentStatusManager initialized for agent_id '{self.context.agent_id}'. "
            f"Initial status: {self.context.current_status.value}. Notifier provided: {bool(notifier)}"
        )

    async def _execute_lifecycle_processors(self, old_status: AgentStatus, new_status: AgentStatus, event_data: Optional[Dict[str, Any]] = None):
        """
        Execute lifecycle processors for the given status update.
        Maps internal status changes to simple LifecycleEvent values.
        """
        from autobyteus.agent.lifecycle import LifecycleEvent
        
        # Map status changes to lifecycle events
        lifecycle_event = None
        if old_status == AgentStatus.BOOTSTRAPPING and new_status == AgentStatus.IDLE:
            lifecycle_event = LifecycleEvent.AGENT_READY
        elif new_status == AgentStatus.AWAITING_LLM_RESPONSE:
            lifecycle_event = LifecycleEvent.BEFORE_LLM_CALL
        elif old_status == AgentStatus.AWAITING_LLM_RESPONSE and new_status == AgentStatus.ANALYZING_LLM_RESPONSE:
            lifecycle_event = LifecycleEvent.AFTER_LLM_RESPONSE
        elif new_status == AgentStatus.EXECUTING_TOOL:
            lifecycle_event = LifecycleEvent.BEFORE_TOOL_EXECUTE
        elif old_status == AgentStatus.EXECUTING_TOOL:
            lifecycle_event = LifecycleEvent.AFTER_TOOL_EXECUTE
        elif new_status == AgentStatus.SHUTTING_DOWN:
            lifecycle_event = LifecycleEvent.AGENT_SHUTTING_DOWN
        
        if lifecycle_event is None:
            return
        
        # Find and execute matching processors
        processors_to_run = [
            p for p in self.context.config.lifecycle_processors
            if p.event == lifecycle_event
        ]
        
        if not processors_to_run:
            return
        
        # Sort by order
        sorted_processors = sorted(processors_to_run, key=lambda p: p.get_order())
        processor_names = [p.get_name() for p in sorted_processors]
        logger.info(f"Agent '{self.context.agent_id}': Executing {len(sorted_processors)} lifecycle processors for '{lifecycle_event.value}': {processor_names}")
        
        for processor in sorted_processors:
            try:
                await processor.process(self.context, event_data or {})
                logger.debug(f"Agent '{self.context.agent_id}': Lifecycle processor '{processor.get_name()}' executed successfully.")
            except Exception as e:
                logger.error(f"Agent '{self.context.agent_id}': Error executing lifecycle processor "
                             f"'{processor.get_name()}' for '{lifecycle_event.value}': {e}",
                             exc_info=True)

    async def emit_status_update(self,
                                 old_status: AgentStatus,
                                 new_status: AgentStatus,
                                 additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emits notifier events and lifecycle processors for a status update
        derived from the event stream.
        """
        if old_status == new_status:
            return

        await self._execute_lifecycle_processors(old_status, new_status, additional_data)
        self.notifier.notify_status_updated(new_status, old_status, additional_data)
