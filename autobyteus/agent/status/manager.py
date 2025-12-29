
# file: autobyteus/autobyteus/agent/status/manager.py
import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.status.transition_decorator import status_transition


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.tool_invocation import ToolInvocation
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier


logger = logging.getLogger(__name__)

class AgentStatusManager:
    """
    Manages the operational status of an agent.
    Responsible for executing state transitions, running lifecycle processors,
    and notifying external listeners.
    Renamed from the legacy manager.
    """
    @property
    def notifier(self) -> 'AgentExternalEventNotifier':
        if self._notifier:
            return self._notifier
        return self.context.get_notifier()

    def __init__(self, context: 'AgentContext', notifier: Optional['AgentExternalEventNotifier'] = None):
        self.context: 'AgentContext' = context
        self._notifier = notifier
        self.context.current_status = AgentStatus.UNINITIALIZED
        
        logger.debug(f"AgentStatusManager initialized for agent_id '{self.context.agent_id}'. "
                     f"Initial status: {self.context.current_status.value}. Notifier provided: {bool(notifier)}")



    async def _execute_lifecycle_processors(self, old_status: AgentStatus, new_status: AgentStatus, event_data: Optional[Dict[str, Any]] = None):
        """
        Execute lifecycle processors for the given status transition.
        Maps internal status transitions to simple LifecycleEvent values.
        """
        from autobyteus.agent.lifecycle import LifecycleEvent
        
        # Map status transitions to lifecycle events
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

    async def _transition_status(self, new_status: AgentStatus,
                                notify_method_name: str,
                                additional_data: Optional[Dict[str, Any]] = None):
        """
        Private async helper to change the agent's status, execute lifecycle processors,
        and then call the appropriate notifier method.
        """
        if not isinstance(new_status, AgentStatus):
            logger.error(f"AgentStatusManager for '{self.context.agent_id}' received invalid type for new_status: {type(new_status)}. Must be AgentStatus.")
            return

        old_status = self.context.current_status
        
        if old_status == new_status:
            logger.debug(f"AgentStatusManager for '{self.context.agent_id}': already in status {new_status.value}. No transition.")
            return

        logger.info(f"Agent '{self.context.agent_id}' status transitioning from {old_status.value} to {new_status.value}.")
        self.context.current_status = new_status

        # Execute and wait for lifecycle processors to complete *before* notifying externally.
        await self._execute_lifecycle_processors(old_status, new_status, additional_data)

        notifier_method = getattr(self.notifier, notify_method_name, None)
        if notifier_method and callable(notifier_method):
            # Pass old_status as it is required by the renamed notifier methods
            notify_args = {"old_status": old_status}
            if additional_data:
                notify_args.update(additional_data)
            
            notifier_method(**notify_args)
        else: 
            logger.error(f"AgentStatusManager for '{self.context.agent_id}': Notifier method '{notify_method_name}' not found or not callable on {type(self.notifier).__name__}.")

    @status_transition(
        source_statuses=[AgentStatus.SHUTDOWN_COMPLETE, AgentStatus.ERROR],
        target_status=AgentStatus.UNINITIALIZED,
        description="Triggered when the agent runtime is started or restarted after being in a terminal state."
    )
    async def notify_runtime_starting_and_uninitialized(self) -> None:
        if self.context.current_status == AgentStatus.UNINITIALIZED:
            await self._transition_status(AgentStatus.UNINITIALIZED, "notify_status_uninitialized_entered")
        elif self.context.current_status.is_terminal():
             await self._transition_status(AgentStatus.UNINITIALIZED, "notify_status_uninitialized_entered")
        else:
            logger.warning(f"Agent '{self.context.agent_id}' notify_runtime_starting_and_uninitialized called in unexpected status: {self.context.current_status.value}")

    @status_transition(
        source_statuses=[AgentStatus.UNINITIALIZED],
        target_status=AgentStatus.BOOTSTRAPPING,
        description="Occurs when the agent's internal bootstrapping process begins."
    )
    async def notify_bootstrapping_started(self) -> None:
        await self._transition_status(AgentStatus.BOOTSTRAPPING, "notify_status_bootstrapping_started")

    @status_transition(
        source_statuses=[AgentStatus.BOOTSTRAPPING],
        target_status=AgentStatus.IDLE,
        description="Occurs when the agent successfully completes bootstrapping and is ready for input."
    )
    async def notify_initialization_complete(self) -> None:
        if self.context.current_status.is_initializing() or self.context.current_status == AgentStatus.UNINITIALIZED:
            # This will now be a BOOTSTRAPPING -> IDLE transition
            await self._transition_status(AgentStatus.IDLE, "notify_status_idle_entered")
        else:
            logger.warning(f"Agent '{self.context.agent_id}' notify_initialization_complete called in unexpected status: {self.context.current_status.value}")

    @status_transition(
        source_statuses=[
            AgentStatus.IDLE, AgentStatus.ANALYZING_LLM_RESPONSE,
            AgentStatus.PROCESSING_TOOL_RESULT, AgentStatus.EXECUTING_TOOL,
            AgentStatus.TOOL_DENIED
        ],
        target_status=AgentStatus.PROCESSING_USER_INPUT,
        description="Fires when the agent begins processing a new user message or inter-agent message."
    )
    async def notify_processing_input_started(self, trigger_info: Optional[str] = None) -> None:
        if self.context.current_status in [AgentStatus.IDLE, AgentStatus.ANALYZING_LLM_RESPONSE, AgentStatus.PROCESSING_TOOL_RESULT, AgentStatus.EXECUTING_TOOL, AgentStatus.TOOL_DENIED]:
            data = {"trigger_info": trigger_info} if trigger_info else {}
            await self._transition_status(AgentStatus.PROCESSING_USER_INPUT, "notify_status_processing_user_input_started", additional_data=data)
        elif self.context.current_status == AgentStatus.PROCESSING_USER_INPUT:
             logger.debug(f"Agent '{self.context.agent_id}' already in PROCESSING_USER_INPUT status.")
        else:
             logger.warning(f"Agent '{self.context.agent_id}' notify_processing_input_started called in unexpected status: {self.context.current_status.value}")

    @status_transition(
        source_statuses=[AgentStatus.PROCESSING_USER_INPUT, AgentStatus.PROCESSING_TOOL_RESULT],
        target_status=AgentStatus.AWAITING_LLM_RESPONSE,
        description="Occurs just before the agent makes a call to the LLM."
    )
    async def notify_awaiting_llm_response(self) -> None:
        await self._transition_status(AgentStatus.AWAITING_LLM_RESPONSE, "notify_status_awaiting_llm_response_started")

    @status_transition(
        source_statuses=[AgentStatus.AWAITING_LLM_RESPONSE],
        target_status=AgentStatus.ANALYZING_LLM_RESPONSE,
        description="Occurs after the agent has received a complete response from the LLM and begins to analyze it."
    )
    async def notify_analyzing_llm_response(self) -> None:
        await self._transition_status(AgentStatus.ANALYZING_LLM_RESPONSE, "notify_status_analyzing_llm_response_started")

    @status_transition(
        source_statuses=[AgentStatus.ANALYZING_LLM_RESPONSE],
        target_status=AgentStatus.AWAITING_TOOL_APPROVAL,
        description="Occurs if the agent proposes a tool use that requires manual user approval."
    )
    async def notify_tool_execution_pending_approval(self, tool_invocation: 'ToolInvocation') -> None:
        await self._transition_status(AgentStatus.AWAITING_TOOL_APPROVAL, "notify_status_awaiting_tool_approval_started")

    @status_transition(
        source_statuses=[AgentStatus.AWAITING_TOOL_APPROVAL],
        target_status=AgentStatus.EXECUTING_TOOL,
        description="Occurs after a pending tool use has been approved and is about to be executed."
    )
    async def notify_tool_execution_resumed_after_approval(self, approved: bool, tool_name: Optional[str]) -> None:
        if approved and tool_name:
            await self._transition_status(AgentStatus.EXECUTING_TOOL, "notify_status_executing_tool_started", additional_data={"tool_name": tool_name})
        else:
            logger.info(f"Agent '{self.context.agent_id}' tool execution denied for '{tool_name}'. Transitioning to allow LLM to process denial.")
            await self.notify_tool_denied(tool_name)

    @status_transition(
        source_statuses=[AgentStatus.AWAITING_TOOL_APPROVAL],
        target_status=AgentStatus.TOOL_DENIED,
        description="Occurs after a pending tool use has been denied by the user."
    )
    async def notify_tool_denied(self, tool_name: Optional[str]) -> None:
        """Notifies that a tool execution has been denied."""
        await self._transition_status(
            AgentStatus.TOOL_DENIED,
            "notify_status_tool_denied_started",
            additional_data={"tool_name": tool_name, "denial_for_tool": tool_name}
        )

    @status_transition(
        source_statuses=[AgentStatus.ANALYZING_LLM_RESPONSE],
        target_status=AgentStatus.EXECUTING_TOOL,
        description="Occurs when an agent with auto-approval executes a tool."
    )
    async def notify_tool_execution_started(self, tool_name: str) -> None:
        await self._transition_status(AgentStatus.EXECUTING_TOOL, "notify_status_executing_tool_started", additional_data={"tool_name": tool_name})

    @status_transition(
        source_statuses=[AgentStatus.EXECUTING_TOOL],
        target_status=AgentStatus.PROCESSING_TOOL_RESULT,
        description="Fires after a tool has finished executing and the agent begins processing its result."
    )
    async def notify_processing_tool_result(self, tool_name: str) -> None:
        await self._transition_status(AgentStatus.PROCESSING_TOOL_RESULT, "notify_status_processing_tool_result_started", additional_data={"tool_name": tool_name})

    @status_transition(
        source_statuses=[
            AgentStatus.PROCESSING_USER_INPUT, AgentStatus.ANALYZING_LLM_RESPONSE,
            AgentStatus.PROCESSING_TOOL_RESULT
        ],
        target_status=AgentStatus.IDLE,
        description="Occurs when an agent completes a processing cycle and is waiting for new input."
    )
    async def notify_processing_complete_and_idle(self) -> None:
        if not self.context.current_status.is_terminal() and self.context.current_status != AgentStatus.IDLE:
            await self._transition_status(AgentStatus.IDLE, "notify_status_idle_entered")
        elif self.context.current_status == AgentStatus.IDLE:
            logger.debug(f"Agent '{self.context.agent_id}' processing complete, already IDLE.")
        else:
            logger.warning(f"Agent '{self.context.agent_id}' notify_processing_complete_and_idle called in unexpected status: {self.context.current_status.value}")

    @status_transition(
        source_statuses=[
            AgentStatus.UNINITIALIZED, AgentStatus.BOOTSTRAPPING, AgentStatus.IDLE,
            AgentStatus.PROCESSING_USER_INPUT, AgentStatus.AWAITING_LLM_RESPONSE,
            AgentStatus.ANALYZING_LLM_RESPONSE, AgentStatus.AWAITING_TOOL_APPROVAL,
            AgentStatus.TOOL_DENIED, AgentStatus.EXECUTING_TOOL,
            AgentStatus.PROCESSING_TOOL_RESULT, AgentStatus.SHUTTING_DOWN
        ],
        target_status=AgentStatus.ERROR,
        description="A catch-all transition that can occur from any non-terminal state if an unrecoverable error happens."
    )
    async def notify_error_occurred(self, error_message: str, error_details: Optional[str] = None) -> None:
        if self.context.current_status != AgentStatus.ERROR:
            data = {"error_message": error_message, "error_details": error_details}
            await self._transition_status(AgentStatus.ERROR, "notify_status_error_entered", additional_data=data)
        else:
            logger.debug(f"Agent '{self.context.agent_id}' already in ERROR status when another error notified: {error_message}")

    @status_transition(
        source_statuses=[
            AgentStatus.UNINITIALIZED, AgentStatus.BOOTSTRAPPING, AgentStatus.IDLE,
            AgentStatus.PROCESSING_USER_INPUT, AgentStatus.AWAITING_LLM_RESPONSE,
            AgentStatus.ANALYZING_LLM_RESPONSE, AgentStatus.AWAITING_TOOL_APPROVAL,
            AgentStatus.TOOL_DENIED, AgentStatus.EXECUTING_TOOL,
            AgentStatus.PROCESSING_TOOL_RESULT
        ],
        target_status=AgentStatus.SHUTTING_DOWN,
        description="Fires when the agent begins its graceful shutdown sequence."
    )
    async def notify_shutdown_initiated(self) -> None:
        if not self.context.current_status.is_terminal():
             await self._transition_status(AgentStatus.SHUTTING_DOWN, "notify_status_shutting_down_started")
        else:
            logger.debug(f"Agent '{self.context.agent_id}' shutdown initiated but already in a terminal status: {self.context.current_status.value}")

    @status_transition(
        source_statuses=[AgentStatus.SHUTTING_DOWN],
        target_status=AgentStatus.SHUTDOWN_COMPLETE,
        description="The final transition when the agent has successfully shut down and released its resources."
    )
    async def notify_final_shutdown_complete(self) -> None:
        final_status = AgentStatus.ERROR if self.context.current_status == AgentStatus.ERROR else AgentStatus.SHUTDOWN_COMPLETE
        if final_status == AgentStatus.ERROR:
            await self._transition_status(AgentStatus.ERROR, "notify_status_error_entered", additional_data={"error_message": "Shutdown completed with agent in error state."})
        else:
            await self._transition_status(AgentStatus.SHUTDOWN_COMPLETE, "notify_status_shutdown_completed")
