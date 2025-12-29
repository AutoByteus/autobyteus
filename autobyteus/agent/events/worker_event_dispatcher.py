# file: autobyteus/autobyteus/agent/events/worker_event_dispatcher.py
import logging
import traceback
from typing import TYPE_CHECKING

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.status.status_update_utils import apply_event_and_derive_status
from autobyteus.agent.events.agent_events import ( # Updated relative import path if needed, but BaseEvent is fine
    BaseEvent,
    AgentErrorEvent,
    AgentIdleEvent,
    LLMCompleteResponseReceivedEvent,
)

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.handlers import EventHandlerRegistry
logger = logging.getLogger(__name__)

class WorkerEventDispatcher:
    """
    Responsible for dispatching events to their appropriate handlers within an AgentWorker.
    It also manages related status updates that occur immediately before or after
    an event is handled. This component is part of the agent's event system.
    """

    def __init__(self,
                 event_handler_registry: 'EventHandlerRegistry'):
        """
        Initializes the WorkerEventDispatcher.

        Args:
            event_handler_registry: The registry for event handlers.
        """
        self.event_handler_registry: 'EventHandlerRegistry' = event_handler_registry
        logger.debug("WorkerEventDispatcher initialized.")

    async def dispatch(self, event: BaseEvent, context: 'AgentContext') -> None: # pragma: no cover
        """
        Dispatches an event to its registered handler and manages status updates.
        """
        event_class = type(event)
        handler = self.event_handler_registry.get_handler(event_class)
        agent_id = context.agent_id 

        try:
            await apply_event_and_derive_status(event, context)
        except Exception as e:  # pragma: no cover
            logger.error(f"WorkerEventDispatcher '{agent_id}': Status projection failed: {e}", exc_info=True)

        if handler:
            event_class_name = event_class.__name__
            handler_class_name = type(handler).__name__

            try:
                logger.debug(f"WorkerEventDispatcher '{agent_id}' (Status: {context.current_status.value}) dispatching '{event_class_name}' to {handler_class_name}.")
                await handler.handle(event, context) 
                logger.debug(f"WorkerEventDispatcher '{agent_id}' (Status: {context.current_status.value}) event '{event_class_name}' handled by {handler_class_name}.")

            except Exception as e: 
                error_details = traceback.format_exc()
                error_msg = f"WorkerEventDispatcher '{agent_id}' error handling '{event_class_name}' with {handler_class_name}: {e}"
                logger.error(error_msg, exc_info=True)
                await context.input_event_queues.enqueue_internal_system_event(
                    AgentErrorEvent(error_message=error_msg, exception_details=error_details)
                )
            else:
                if isinstance(event, LLMCompleteResponseReceivedEvent):
                    if context.current_status == AgentStatus.ANALYZING_LLM_RESPONSE and \
                       not context.state.pending_tool_approvals and \
                       context.input_event_queues.tool_invocation_request_queue.empty():
                           await context.input_event_queues.enqueue_internal_system_event(AgentIdleEvent())
        else: 
            logger.warning(f"WorkerEventDispatcher '{agent_id}' (Status: {context.current_status.value}) No handler for '{event_class.__name__}'. Event: {event}")
