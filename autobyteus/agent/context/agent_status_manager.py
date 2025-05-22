# file: autobyteus/autobyteus/agent/context/agent_status_manager.py
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.agent.status import AgentStatus
from autobyteus.events.event_types import EventType as ExternalEventType
from autobyteus.events.event_emitter import EventEmitter # ADDED IMPORT

if TYPE_CHECKING:
    from autobyteus.agent.context.agent_context import AgentContext
    # EventEmitter was previously imported from autobyteus.events.event_emitter for type hint only
    # Now it's a base class.

logger = logging.getLogger(__name__)

class AgentStatusManager(EventEmitter): # MODIFIED: Inherit from EventEmitter
    """
    Manages the status transitions of an agent.
    It is informed of events and conditions by the AgentRuntime and updates
    the AgentContext's status accordingly, emitting external notifications.
    It also sets the initial concrete status of the agent on the context.
    Now, it is an EventEmitter itself for status-related events.
    """
    def __init__(self, context: 'AgentContext'): # MODIFIED: Removed emitter parameter
        """
        Initializes the AgentStatusManager and sets the initial status
        on the provided agent context.

        Args:
            context: The agent's context, where the status is stored and managed.
        """
        super().__init__() # ADDED: Call EventEmitter's __init__
        self.context: 'AgentContext' = context
        # self.emitter is no longer needed as this class is now the emitter.
        
        self.context.status = AgentStatus.NOT_STARTED
        
        logger.debug(f"AgentStatusManager initialized for agent_id '{self.context.agent_id}'. "
                     f"Context status set to: {self.context.status.value}")

    def _change_status(self, new_status: AgentStatus) -> None:
        """
        Private helper to change the status in context, log the change, and emit an external event.
        """
        if not isinstance(new_status, AgentStatus):
            logger.error(f"AgentStatusManager for '{self.context.agent_id}' received invalid type for new_status: {type(new_status)}. Must be AgentStatus.")
            return

        old_status = self.context.status 
        
        if old_status == new_status:
            logger.debug(f"AgentStatusManager for '{self.context.agent_id}': status already {new_status.value}. No change.")
            return

        logger.info(f"Agent '{self.context.agent_id}' status changing from {old_status.value} to {new_status.value}.")
        self.context.status = new_status 

        # MODIFIED: Call self.emit instead of self.emitter.emit
        self.emit(
            ExternalEventType.AGENT_STATUS_CHANGED,
            agent_id=self.context.agent_id,
            new_status=new_status.value,
            old_status=old_status.value 
        )
        logger.debug(f"AgentStatusManager for '{self.context.agent_id}' confirmed status change to {new_status.value} and emitted event.")

    def notify_runtime_starting(self) -> None:
        """Called when the AgentRuntime's execution loop is being started."""
        if self.context.status in [AgentStatus.NOT_STARTED, AgentStatus.ENDED, AgentStatus.ERROR]:
            self._change_status(AgentStatus.STARTING)
        elif self.context.status == AgentStatus.STARTING:
            logger.debug(f"Agent '{self.context.agent_id}' already in STARTING state via StatusManager.")
        else:
            logger.warning(f"Agent '{self.context.agent_id}' notify_runtime_starting called in unexpected state: {self.context.status.value}")


    def notify_agent_started_event_handled(self) -> None:
        """Called after an AgentStartedEvent has been processed (logged)."""
        if self.context.status == AgentStatus.STARTING:
            self._change_status(AgentStatus.IDLE)
            # MODIFIED: Call self.emit
            self.emit(ExternalEventType.AGENT_STARTED, agent_id=self.context.agent_id)
            logger.info(f"AgentStatusManager for '{self.context.agent_id}' transitioned to IDLE and emitted AGENT_STARTED.")
        else:
            logger.warning(f"Agent '{self.context.agent_id}' notify_agent_started_event_handled called in unexpected state: {self.context.status.value}")


    def notify_processing_event_dequeued(self) -> None:
        """Called when a new processing event is dequeued and agent is IDLE."""
        if self.context.status == AgentStatus.IDLE:
            self._change_status(AgentStatus.RUNNING)
        elif self.context.status == AgentStatus.RUNNING:
            logger.debug(f"Agent '{self.context.agent_id}' received processing event while already RUNNING.")
        else: 
             logger.warning(f"Agent '{self.context.agent_id}' notify_processing_event_dequeued called in unexpected state: {self.context.status.value}")


    def notify_processing_complete_queues_empty(self) -> None:
        """Called when processing of an event is complete and input queues are empty."""
        if self.context.status == AgentStatus.RUNNING:
            self._change_status(AgentStatus.IDLE)
        elif self.context.status == AgentStatus.IDLE:
            logger.debug(f"Agent '{self.context.agent_id}' processing complete, already IDLE.")
        else:
            logger.warning(f"Agent '{self.context.agent_id}' notify_processing_complete_queues_empty called in unexpected state: {self.context.status.value}")


    def notify_error_occurred(self) -> None:
        """Called when an error occurs (e.g., in a handler or the execution loop)."""
        if self.context.status != AgentStatus.ERROR:
            self._change_status(AgentStatus.ERROR)
        else:
            logger.debug(f"Agent '{self.context.agent_id}' already in ERROR state when another error notified.")


    def notify_runtime_stopping_or_loop_ended_unexpectedly(self) -> None:
        """
        Called when the runtime is preparing to stop (due to stop request)
        or if the execution loop terminates unexpectedly.
        This method primarily handles transitions to ENDED if not already in ERROR.
        """
        if self.context.status != AgentStatus.ERROR and self.context.status != AgentStatus.ENDED:
            self._change_status(AgentStatus.ENDED)
        elif self.context.status == AgentStatus.ERROR:
            logger.info(f"Agent '{self.context.agent_id}' loop ending/stopped while in ERROR state. Status remains ERROR.")
        elif self.context.status == AgentStatus.ENDED:
            logger.debug(f"Agent '{self.context.agent_id}' loop ending/stopped, already ENDED.")


    def notify_final_shutdown_complete(self) -> None:
        """Called after the AgentRuntime's stop_execution_loop has fully completed all cleanup."""
        if self.context.status != AgentStatus.ERROR: # Ensure final status is ENDED or ERROR
            current_status = self.context.status
            if current_status != AgentStatus.ENDED:
                 self._change_status(AgentStatus.ENDED)
        
        logger.info(f"AgentStatusManager for '{self.context.agent_id}' confirmed final state: {self.context.status.value} post-shutdown.")
        # MODIFIED: Call self.emit
        self.emit(ExternalEventType.AGENT_STOPPED, agent_id=self.context.agent_id, status=self.context.status.value)
