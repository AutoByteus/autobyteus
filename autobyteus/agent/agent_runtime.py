# file: autobyteus/autobyteus/agent/agent_runtime.py
import asyncio
import logging
import traceback 
from typing import Dict, Optional, Any, AsyncIterator, Type, cast

from autobyteus.agent.context.agent_context import AgentContext 
from autobyteus.agent.phases import AgentOperationalPhase 
from autobyteus.agent.notifiers import AgentExternalEventNotifier 

from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager 
from autobyteus.agent.events import (
    BaseEvent,
    AgentReadyEvent, # MODIFIED: Renamed from AgentStartedEvent
    AgentStoppedEvent, 
    AgentErrorEvent,   
    BootstrapAgentEvent,
    LLMUserMessageReadyEvent, 
    PendingToolInvocationEvent, 
    ToolExecutionApprovalEvent,
    ToolResultEvent, 
    LLMCompleteResponseReceivedEvent, 
    UserMessageReceivedEvent, 
    InterAgentMessageReceivedEvent 
)
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry


logger = logging.getLogger(__name__)

class AgentRuntime:
    """
    The active execution engine for an agent.
    Manages the agent's lifecycle, event loop, and dispatches events to handlers.
    Agent operational phase management is delegated to an AgentPhaseManager,
    which uses an AgentExternalEventNotifier to signal phase changes.
    Initialization is triggered by a BootstrapAgentEvent.
    """

    def __init__(self,
                 context: AgentContext, 
                 event_handler_registry: EventHandlerRegistry):
        
        if not isinstance(context, AgentContext): 
            raise TypeError(f"AgentRuntime requires a composite AgentContext instance. Got {type(context)}")

        self.context: AgentContext = context 
        self.event_handler_registry: EventHandlerRegistry = event_handler_registry
        
        self._main_loop_task: Optional[asyncio.Task] = None
        self._is_running_flag: bool = False 
        self._stop_requested: asyncio.Event = asyncio.Event()
            
        self.external_event_notifier: AgentExternalEventNotifier = AgentExternalEventNotifier(agent_id=self.context.agent_id)
        self.phase_manager: AgentPhaseManager = AgentPhaseManager(context=self.context, notifier=self.external_event_notifier) 
        
        self.context.state.phase_manager_ref = self.phase_manager 
        logger.debug(f"AgentRuntime '{self.context.agent_id}': phase_manager_ref set on context.state, pointing to AgentPhaseManager.")

        logger.info(f"AgentRuntime initialized for agent_id '{self.context.agent_id}'. Definition: '{self.context.definition.name}'")
        registered_handlers_info = [cls.__name__ for cls in self.event_handler_registry.get_all_registered_event_types()]
        logger.debug(f"AgentRuntime '{self.context.agent_id}' configured with event_handler_registry for event types: {registered_handlers_info}")

    def start_execution_loop(self) -> None:
        if self.is_running: 
            logger.warning(f"AgentRuntime for '{self.context.agent_id}' is already running. Ignoring start request.")
            return

        self._is_running_flag = True 
        self._stop_requested.clear()
        
        self.phase_manager.notify_runtime_starting_and_uninitialized() # Phase becomes UNINITIALIZED
            
        self._main_loop_task = asyncio.create_task(self._execution_loop(), name=f"agent_runtime_loop_{self.context.agent_id}")
        logger.info(f"AgentRuntime for '{self.context.agent_id}' execution loop task created. Will trigger bootstrap chain via BootstrapAgentEvent.")

    async def _enqueue_fallback_sentinels(self): # pragma: no cover
        logger.debug(f"AgentRuntime '{self.context.agent_id}' enqueuing fallback sentinels to output queues.")
        output_queue_names = [
            "assistant_output_chunk_queue", "assistant_final_message_queue",
            "tool_interaction_log_queue", "pending_tool_approval_queue" 
        ]
        for queue_name in output_queue_names:
            try:
                await self.context.output_data_queues.enqueue_end_of_stream_sentinel_to_output_queue(queue_name)
            except Exception as e: 
                logger.error(f"AgentRuntime '{self.context.agent_id}' failed to enqueue fallback sentinel to '{queue_name}': {e}", exc_info=True)
        

    async def stop_execution_loop(self, timeout: float = 10.0) -> None: # pragma: no cover
        if not self._is_running_flag: 
            logger.warning(f"AgentRuntime for '{self.context.agent_id}' is not running or already stopped. Ignoring stop request.")
            return
        
        if self._stop_requested.is_set():
             logger.info(f"AgentRuntime for '{self.context.agent_id}' stop already in progress.")
             if self._main_loop_task and not self._main_loop_task.done():
                 try: await asyncio.wait_for(self._main_loop_task, timeout=timeout)
                 except asyncio.TimeoutError: logger.warning(f"AgentRuntime for '{self.context.agent_id}' timed out waiting for already stopping loop to complete.")
                 except asyncio.CancelledError: pass 
             self._is_running_flag = False 
             return

        logger.info(f"AgentRuntime for '{self.context.agent_id}' execution loop stop requested (timeout: {timeout}s).")
        self._stop_requested.set() 
        self.phase_manager.notify_shutdown_initiated() 

        await self.context.input_event_queues.enqueue_internal_system_event(AgentStoppedEvent()) 

        if self._main_loop_task and not self._main_loop_task.done():
            try:
                await asyncio.wait_for(self._main_loop_task, timeout=timeout)
                logger.info(f"AgentRuntime for '{self.context.agent_id}' execution loop stopped gracefully.")
            except asyncio.TimeoutError:
                logger.warning(f"AgentRuntime for '{self.context.agent_id}' execution loop timed out during stop. Forcing cancellation.")
                self._main_loop_task.cancel()
                try: await self._main_loop_task 
                except asyncio.CancelledError: logger.info(f"AgentRuntime for '{self.context.agent_id}' execution loop task was cancelled.")
            except Exception as e: 
                logger.error(f"Exception during AgentRuntime '{self.context.agent_id}' stop's wait_for: {e}", exc_info=True)
                self.phase_manager.notify_error_occurred(str(e), traceback.format_exc()) 

        await self._enqueue_fallback_sentinels()
        await self.context.output_data_queues.graceful_shutdown(timeout=max(1.0, timeout / 2)) 
        if self.context.llm_instance and hasattr(self.context.llm_instance, 'cleanup'): 
            await self.context.llm_instance.cleanup() 
        
        self._is_running_flag = False 
        self._main_loop_task = None 

        self.phase_manager.notify_final_shutdown_complete() 
        
        logger.info(f"AgentRuntime for '{self.context.agent_id}' stop_execution_loop completed. Final phase: {self.context.current_phase.value}")


    async def _execution_loop(self) -> None:
        # Enqueue BootstrapAgentEvent to start the initialization sequence
        await self.context.input_event_queues.enqueue_internal_system_event(BootstrapAgentEvent()) 
        logger.info(f"Agent '{self.context.agent_id}' _execution_loop: Task starting. Enqueued BootstrapAgentEvent. Phase should be UNINITIALIZED.")

        try:
            while not self._stop_requested.is_set():
                try:
                    queue_event_tuple = await asyncio.wait_for(
                        self.context.input_event_queues.get_next_input_event(), timeout=0.5 
                    )
                except asyncio.TimeoutError:
                    current_q_phase = self.context.current_phase 
                    if current_q_phase.is_processing() and not current_q_phase.is_terminal() and \
                       all(q.empty() for _, q in self.context.input_event_queues._input_queues if q is not None): 
                         if current_q_phase != AgentOperationalPhase.IDLE : 
                            self.phase_manager.notify_processing_complete_and_idle() 
                    continue 

                if queue_event_tuple is None: 
                    if self._stop_requested.is_set(): break
                    continue

                _queue_name, event_obj = queue_event_tuple
                
                if not isinstance(event_obj, BaseEvent): 
                    logger.warning(f"Agent '{self.context.agent_id}' _execution_loop: Non-BaseEvent from '{_queue_name}': {type(event_obj)}. Skipping.")
                    continue
                
                current_phase_before_dispatch = self.context.current_phase 

                # If IDLE and a processing event comes in, transition phase
                if current_phase_before_dispatch == AgentOperationalPhase.IDLE:
                    if isinstance(event_obj, (UserMessageReceivedEvent, InterAgentMessageReceivedEvent)):
                        self.phase_manager.notify_processing_input_started(trigger_info=type(event_obj).__name__)
                
                await self._dispatch_event(event_obj, current_phase_before_dispatch) 
                
                await asyncio.sleep(0) 
                
        except asyncio.CancelledError: # pragma: no cover
            logger.info(f"Agent '{self.context.agent_id}' _execution_loop was cancelled.")
        except Exception as e: # pragma: no cover
            error_details = traceback.format_exc()
            logger.error(f"Fatal error in Agent '{self.context.agent_id}' _execution_loop: {e}", exc_info=True)
            self.phase_manager.notify_error_occurred(str(e), error_details) 
            await self.context.input_event_queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=str(e), exception_details=error_details)
            )
        finally: # pragma: no branch
            logger.info(f"Agent '{self.context.agent_id}' _execution_loop is exiting. Stop requested: {self._stop_requested.is_set()}")
            if not self._stop_requested.is_set() and not self.context.current_phase.is_terminal(): # pragma: no cover
                current_error_details = traceback.format_exc() if 'error_details' not in locals() or error_details is None else error_details
                self.phase_manager.notify_error_occurred("Execution loop ended unexpectedly.", current_error_details)
            
            if hasattr(self.context.input_event_queues, 'log_remaining_items_at_shutdown'): # pragma: no cover
                 self.context.input_event_queues.log_remaining_items_at_shutdown()

            self._is_running_flag = False 
            logger.info(f"Agent '{self.context.agent_id}' _execution_loop has finished.")


    async def _dispatch_event(self, event: BaseEvent, current_phase_before_dispatch: AgentOperationalPhase) -> None: # pragma: no cover
        event_class = type(event)
        handler = self.event_handler_registry.get_handler(event_class)

        if handler:
            event_class_name = event_class.__name__
            handler_class_name = type(handler).__name__

            if isinstance(event, LLMUserMessageReadyEvent):
                if current_phase_before_dispatch not in [AgentOperationalPhase.AWAITING_LLM_RESPONSE, AgentOperationalPhase.ERROR]:
                    self.phase_manager.notify_awaiting_llm_response()
            elif isinstance(event, PendingToolInvocationEvent):
                if not self.context.auto_execute_tools:
                    self.phase_manager.notify_tool_execution_pending_approval(event.tool_invocation)
                else: 
                    self.phase_manager.notify_tool_execution_started(event.tool_invocation.name)
            elif isinstance(event, ToolExecutionApprovalEvent):
                tool_name_for_approval: Optional[str] = None
                pending_invocation = self.context.pending_tool_approvals.get(event.tool_invocation_id) 
                if pending_invocation:
                    tool_name_for_approval = pending_invocation.name
                else: 
                    logger.warning(f"Agent '{self.context.agent_id}': Could not find pending invocation for ID '{event.tool_invocation_id}' to get tool name for phase notification.")
                    tool_name_for_approval = "unknown_tool" # Default or handle as error

                self.phase_manager.notify_tool_execution_resumed_after_approval(
                    approved=event.is_approved, 
                    tool_name=tool_name_for_approval
                )
            elif isinstance(event, ToolResultEvent):
                 if current_phase_before_dispatch == AgentOperationalPhase.EXECUTING_TOOL: 
                    self.phase_manager.notify_processing_tool_result(event.tool_name)

            try:
                logger.debug(f"Agent '{self.context.agent_id}' (Phase: {self.context.current_phase.value}) dispatching '{event_class_name}' to {handler_class_name}.")
                await handler.handle(event, self.context) 
                logger.debug(f"Agent '{self.context.agent_id}' (Phase: {self.context.current_phase.value}) event '{event_class_name}' handled by {handler_class_name}.")

                # If AgentReadyEvent is handled (meaning bootstrap was successful), transition to IDLE
                if isinstance(event, AgentReadyEvent): # MODIFIED: Check for AgentReadyEvent
                    self.phase_manager.notify_initialization_complete() 
                
                # If LLM response is processed and no further tool actions are pending, go to IDLE
                if isinstance(event, LLMCompleteResponseReceivedEvent):
                    if self.context.current_phase == AgentOperationalPhase.ANALYZING_LLM_RESPONSE and \
                       not self.context.pending_tool_approvals and \
                       self.context.input_event_queues.tool_invocation_request_queue.empty(): 
                           self.phase_manager.notify_processing_complete_and_idle()

            except Exception as e: 
                error_details = traceback.format_exc()
                error_msg = f"Agent '{self.context.agent_id}' error handling '{event_class_name}' with {handler_class_name}: {e}"
                logger.error(error_msg, exc_info=True)
                self.phase_manager.notify_error_occurred(error_msg, error_details) 
                await self.context.input_event_queues.enqueue_internal_system_event(
                    AgentErrorEvent(error_message=error_msg, exception_details=error_details)
                )
        else: 
            logger.warning(f"Agent '{self.context.agent_id}' (Phase: {self.context.current_phase.value}) No handler for '{event_class.__name__}'. Event: {event}")


    @property 
    def current_phase_property(self) -> AgentOperationalPhase: 
        return self.context.current_phase 
        
    @property
    def is_running(self) -> bool:
        if self._is_running_flag and self._main_loop_task and not self._main_loop_task.done():
            return not self.context.current_phase.is_terminal()
        return False
