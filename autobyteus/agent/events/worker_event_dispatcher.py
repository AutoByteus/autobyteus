# file: autobyteus/autobyteus/agent/events/worker_event_dispatcher.py
import asyncio
import logging
import traceback
from typing import TYPE_CHECKING, Optional

from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.agent.events.agent_events import ( # Updated relative import path if needed, but BaseEvent is fine
    BaseEvent,
    AgentReadyEvent,
    AgentErrorEvent,
    LLMUserMessageReadyEvent,
    PendingToolInvocationEvent,
    ToolExecutionApprovalEvent,
    ToolResultEvent,
    LLMCompleteResponseReceivedEvent,
    UserMessageReceivedEvent, 
    InterAgentMessageReceivedEvent, 
)

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.handlers import EventHandlerRegistry
    from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager

logger = logging.getLogger(__name__)

class WorkerEventDispatcher:
    """
    Responsible for dispatching events to their appropriate handlers within an AgentWorker.
    It also manages related phase transitions that occur immediately before or after
    an event is handled. This component is part of the agent's event system.
    """

    def __init__(self,
                 event_handler_registry: 'EventHandlerRegistry',
                 phase_manager: 'AgentPhaseManager'):
        """
        Initializes the WorkerEventDispatcher.

        Args:
            event_handler_registry: The registry for event handlers.
            phase_manager: The agent's phase manager.
        """
        self.event_handler_registry: 'EventHandlerRegistry' = event_handler_registry
        self.phase_manager: 'AgentPhaseManager' = phase_manager
        logger.debug("WorkerEventDispatcher initialized.")

    async def dispatch(self, event: BaseEvent, context: 'AgentContext') -> None: # pragma: no cover
        """
        Dispatches an event to its registered handler and manages phase transitions.
        """
        event_class = type(event)
        handler = self.event_handler_registry.get_handler(event_class)
        agent_id = context.agent_id 

        if handler:
            event_class_name = event_class.__name__
            handler_class_name = type(handler).__name__

            current_phase_before_dispatch = context.current_phase

            if current_phase_before_dispatch == AgentOperationalPhase.IDLE:
                if isinstance(event, (UserMessageReceivedEvent, InterAgentMessageReceivedEvent)):
                    await self.phase_manager.notify_processing_input_started(trigger_info=type(event).__name__)
            
            if isinstance(event, LLMUserMessageReadyEvent):
                if current_phase_before_dispatch not in [AgentOperationalPhase.AWAITING_LLM_RESPONSE, AgentOperationalPhase.ERROR]:
                    await self.phase_manager.notify_awaiting_llm_response()
            elif isinstance(event, PendingToolInvocationEvent):
                if not context.auto_execute_tools:
                    await self.phase_manager.notify_tool_execution_pending_approval(event.tool_invocation)
                else: 
                    await self.phase_manager.notify_tool_execution_started(event.tool_invocation.name)
            elif isinstance(event, ToolExecutionApprovalEvent):
                tool_name_for_approval: Optional[str] = None
                pending_invocation = context.state.pending_tool_approvals.get(event.tool_invocation_id) 
                if pending_invocation:
                    tool_name_for_approval = pending_invocation.name
                else: 
                    logger.warning(f"WorkerEventDispatcher '{agent_id}': Could not find pending invocation for ID '{event.tool_invocation_id}' to get tool name for phase notification.")
                    tool_name_for_approval = "unknown_tool" 

                await self.phase_manager.notify_tool_execution_resumed_after_approval(
                    approved=event.is_approved, 
                    tool_name=tool_name_for_approval
                )
            elif isinstance(event, ToolResultEvent):
                 if context.current_phase == AgentOperationalPhase.EXECUTING_TOOL: 
                    await self.phase_manager.notify_processing_tool_result(event.tool_name)
            elif isinstance(event, LLMCompleteResponseReceivedEvent):
                if context.current_phase == AgentOperationalPhase.AWAITING_LLM_RESPONSE:
                    await self.phase_manager.notify_analyzing_llm_response()

            try:
                logger.debug(f"WorkerEventDispatcher '{agent_id}' (Phase: {context.current_phase.value}) dispatching '{event_class_name}' to {handler_class_name}.")
                await handler.handle(event, context) 
                logger.debug(f"WorkerEventDispatcher '{agent_id}' (Phase: {context.current_phase.value}) event '{event_class_name}' handled by {handler_class_name}.")

                if isinstance(event, AgentReadyEvent): 
                    await self.phase_manager.notify_initialization_complete() 
                
                if isinstance(event, LLMCompleteResponseReceivedEvent):
                    if context.current_phase == AgentOperationalPhase.ANALYZING_LLM_RESPONSE and \
                       not context.state.pending_tool_approvals and \
                       context.input_event_queues.tool_invocation_request_queue.empty():
                           await self.phase_manager.notify_processing_complete_and_idle()

            except Exception as e: 
                error_details = traceback.format_exc()
                error_msg = f"WorkerEventDispatcher '{agent_id}' error handling '{event_class_name}' with {handler_class_name}: {e}"
                logger.error(error_msg, exc_info=True)
                await self.phase_manager.notify_error_occurred(error_msg, error_details) 
                await context.input_event_queues.enqueue_internal_system_event(
                    AgentErrorEvent(error_message=error_msg, exception_details=error_details)
                )
        else: 
            logger.warning(f"WorkerEventDispatcher '{agent_id}' (Phase: {context.current_phase.value}) No handler for '{event_class.__name__}'. Event: {event}")
