# file: autobyteus/autobyteus/agent/context/agent_phase_manager.py
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from .phases import AgentOperationalPhase 

if TYPE_CHECKING:
    from autobyteus.agent.context.agent_context import AgentContext
    from autobyteus.agent.tool_invocation import ToolInvocation
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 


logger = logging.getLogger(__name__)

class AgentPhaseManager: 
    """
    Manages the operational phase of an agent and uses an AgentExternalEventNotifier
    to signal phase changes externally.
    It is informed of conditions by AgentRuntime and updates AgentContext.current_phase.
    """
    def __init__(self, context: 'AgentContext', notifier: 'AgentExternalEventNotifier'): 
        self.context: 'AgentContext' = context
        self.notifier: 'AgentExternalEventNotifier' = notifier 

        self.context.current_phase = AgentOperationalPhase.UNINITIALIZED
        
        logger.debug(f"AgentPhaseManager initialized for agent_id '{self.context.agent_id}'. "
                     f"Initial phase: {self.context.current_phase.value}. Uses provided notifier.")

    def _transition_phase(self, new_phase: AgentOperationalPhase, 
                          notify_method_name: str, 
                          additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Private helper to change the agent's phase and call the appropriate notifier method.
        """
        if not isinstance(new_phase, AgentOperationalPhase): 
            logger.error(f"AgentPhaseManager for '{self.context.agent_id}' received invalid type for new_phase: {type(new_phase)}. Must be AgentOperationalPhase.")
            return

        old_phase = self.context.current_phase
        
        if old_phase == new_phase:
            logger.debug(f"AgentPhaseManager for '{self.context.agent_id}': already in phase {new_phase.value}. No transition.")
            return

        logger.info(f"Agent '{self.context.agent_id}' phase transitioning from {old_phase.value} to {new_phase.value}.")
        self.context.current_phase = new_phase

        notifier_method = getattr(self.notifier, notify_method_name, None)
        if notifier_method and callable(notifier_method):
            notify_args = {"old_phase": old_phase}
            if additional_data:
                notify_args.update(additional_data)
            
            notifier_method(**notify_args)
        else: 
            logger.error(f"AgentPhaseManager for '{self.context.agent_id}': Notifier method '{notify_method_name}' not found or not callable on {type(self.notifier).__name__}.")

    def notify_runtime_starting_and_uninitialized(self) -> None:
        if self.context.current_phase == AgentOperationalPhase.UNINITIALIZED:
            self._transition_phase(AgentOperationalPhase.UNINITIALIZED, "notify_phase_uninitialized_entered")
        elif self.context.current_phase.is_terminal(): 
             self._transition_phase(AgentOperationalPhase.UNINITIALIZED, "notify_phase_uninitialized_entered")
        else: 
             logger.warning(f"Agent '{self.context.agent_id}' notify_runtime_starting_and_uninitialized called in unexpected phase: {self.context.current_phase.value}")

    # notify_initializing_tools method removed.

    def notify_initializing_prompt(self) -> None:
        self._transition_phase(AgentOperationalPhase.INITIALIZING_PROMPT, "notify_phase_initializing_prompt_started")

    # notify_initializing_llm method removed.
    
    def notify_initialization_complete(self) -> None:
        if self.context.current_phase.is_initializing() or self.context.current_phase == AgentOperationalPhase.UNINITIALIZED :
            self._transition_phase(AgentOperationalPhase.IDLE, "notify_phase_idle_entered")
        else: 
            logger.warning(f"Agent '{self.context.agent_id}' notify_initialization_complete called in unexpected phase: {self.context.current_phase.value}")

    def notify_processing_input_started(self, trigger_info: Optional[str] = None) -> None:
        if self.context.current_phase in [AgentOperationalPhase.IDLE, AgentOperationalPhase.ANALYZING_LLM_RESPONSE, AgentOperationalPhase.PROCESSING_TOOL_RESULT, AgentOperationalPhase.EXECUTING_TOOL]:
            data = {"trigger_info": trigger_info} if trigger_info else {}
            self._transition_phase(AgentOperationalPhase.PROCESSING_USER_INPUT, "notify_phase_processing_user_input_started", additional_data=data)
        elif self.context.current_phase == AgentOperationalPhase.PROCESSING_USER_INPUT: 
             logger.debug(f"Agent '{self.context.agent_id}' already in PROCESSING_USER_INPUT phase.")
        else: 
             logger.warning(f"Agent '{self.context.agent_id}' notify_processing_input_started called in unexpected phase: {self.context.current_phase.value}")

    def notify_awaiting_llm_response(self) -> None:
        self._transition_phase(AgentOperationalPhase.AWAITING_LLM_RESPONSE, "notify_phase_awaiting_llm_response_started")

    def notify_analyzing_llm_response(self) -> None:
        self._transition_phase(AgentOperationalPhase.ANALYZING_LLM_RESPONSE, "notify_phase_analyzing_llm_response_started")

    def notify_tool_execution_pending_approval(self, tool_invocation: 'ToolInvocation') -> None:
        # The notifier's notify_phase_awaiting_tool_approval_started method no longer takes tool_details.
        # The phase event itself is the signal. Tool data comes via queue.
        self._transition_phase(AgentOperationalPhase.AWAITING_TOOL_APPROVAL, "notify_phase_awaiting_tool_approval_started")

    def notify_tool_execution_resumed_after_approval(self, approved: bool, tool_name: Optional[str]) -> None:
        if approved and tool_name:
            self._transition_phase(AgentOperationalPhase.EXECUTING_TOOL, "notify_phase_executing_tool_started", additional_data={"tool_name": tool_name})
        else:
            logger.info(f"Agent '{self.context.agent_id}' tool execution denied for '{tool_name}'. Transitioning to allow LLM to process denial.")
            self._transition_phase(AgentOperationalPhase.ANALYZING_LLM_RESPONSE, "notify_phase_analyzing_llm_response_started", additional_data={"denial_for_tool": tool_name})


    def notify_tool_execution_started(self, tool_name: str) -> None: 
        self._transition_phase(AgentOperationalPhase.EXECUTING_TOOL, "notify_phase_executing_tool_started", additional_data={"tool_name": tool_name})

    def notify_processing_tool_result(self, tool_name: str) -> None:
        self._transition_phase(AgentOperationalPhase.PROCESSING_TOOL_RESULT, "notify_phase_processing_tool_result_started", additional_data={"tool_name": tool_name})

    def notify_processing_complete_and_idle(self) -> None:
        if not self.context.current_phase.is_terminal() and self.context.current_phase != AgentOperationalPhase.IDLE:
            self._transition_phase(AgentOperationalPhase.IDLE, "notify_phase_idle_entered")
        elif self.context.current_phase == AgentOperationalPhase.IDLE: 
            logger.debug(f"Agent '{self.context.agent_id}' processing complete, already IDLE.")
        else: 
            logger.warning(f"Agent '{self.context.agent_id}' notify_processing_complete_and_idle called in unexpected phase: {self.context.current_phase.value}")

    def notify_error_occurred(self, error_message: str, error_details: Optional[str] = None) -> None:
        if self.context.current_phase != AgentOperationalPhase.ERROR:
            data = {"error_message": error_message, "error_details": error_details}
            self._transition_phase(AgentOperationalPhase.ERROR, "notify_phase_error_entered", additional_data=data)
        else: 
            logger.debug(f"Agent '{self.context.agent_id}' already in ERROR phase when another error notified: {error_message}")

    def notify_shutdown_initiated(self) -> None:
        if not self.context.current_phase.is_terminal():
             self._transition_phase(AgentOperationalPhase.SHUTTING_DOWN, "notify_phase_shutting_down_started")
        else: 
            logger.debug(f"Agent '{self.context.agent_id}' shutdown initiated but already in a terminal phase: {self.context.current_phase.value}")


    def notify_final_shutdown_complete(self) -> None:
        final_phase = AgentOperationalPhase.ERROR if self.context.current_phase == AgentOperationalPhase.ERROR else AgentOperationalPhase.SHUTDOWN_COMPLETE
        if final_phase == AgentOperationalPhase.ERROR:
            self._transition_phase(AgentOperationalPhase.ERROR, "notify_phase_error_entered", additional_data={"error_message": "Shutdown completed with agent in error state."})
        else:
            self._transition_phase(AgentOperationalPhase.SHUTDOWN_COMPLETE, "notify_phase_shutdown_completed")
