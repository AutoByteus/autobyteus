# file: autobyteus/autobyteus/agent/context/agent_phase_manager.py
import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from autobyteus.agent.phases import AgentOperationalPhase, phase_transition

if TYPE_CHECKING:
    from autobyteus.agent.context.agent_context import AgentContext
    from autobyteus.agent.tool_invocation import ToolInvocation
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier


logger = logging.getLogger(__name__)

class AgentPhaseManager:
    """
    Manages the operational phase of an agent, uses an AgentExternalEventNotifier
    to signal phase changes externally, and executes phase transition hooks.
    """
    def __init__(self, context: 'AgentContext', notifier: 'AgentExternalEventNotifier'):
        self.context: 'AgentContext' = context
        self.notifier: 'AgentExternalEventNotifier' = notifier

        self.context.current_phase = AgentOperationalPhase.UNINITIALIZED
        
        logger.debug(f"AgentPhaseManager initialized for agent_id '{self.context.agent_id}'. "
                     f"Initial phase: {self.context.current_phase.value}. Uses provided notifier.")

    async def _execute_hooks(self, old_phase: AgentOperationalPhase, new_phase: AgentOperationalPhase):
        """Asynchronously executes hooks that match the given phase transition."""
        hooks_to_run = [
            hook for hook in self.context.config.phase_hooks
            if hook.source_phase == old_phase and hook.target_phase == new_phase
        ]

        if not hooks_to_run:
            return

        hook_names = [hook.__class__.__name__ for hook in hooks_to_run]
        logger.info(f"Agent '{self.context.agent_id}': Executing {len(hooks_to_run)} hooks for transition "
                    f"'{old_phase.value}' -> '{new_phase.value}': {hook_names}")
        
        for hook in hooks_to_run:
            try:
                await hook.execute(self.context)
                logger.debug(f"Agent '{self.context.agent_id}': Hook '{hook.__class__.__name__}' executed successfully.")
            except Exception as e:
                logger.error(f"Agent '{self.context.agent_id}': Error executing phase transition hook "
                             f"'{hook.__class__.__name__}' for '{old_phase.value}' -> '{new_phase.value}': {e}",
                             exc_info=True)
                # We log the error but do not halt the agent's phase transition.

    async def _transition_phase(self, new_phase: AgentOperationalPhase,
                                notify_method_name: str,
                                additional_data: Optional[Dict[str, Any]] = None):
        """
        Private async helper to change the agent's phase, execute hooks, and then
        call the appropriate notifier method. Hooks are now awaited.
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

        # Execute and wait for hooks to complete *before* notifying externally.
        await self._execute_hooks(old_phase, new_phase)

        notifier_method = getattr(self.notifier, notify_method_name, None)
        if notifier_method and callable(notifier_method):
            notify_args = {"old_phase": old_phase}
            if additional_data:
                notify_args.update(additional_data)
            
            notifier_method(**notify_args)
        else: 
            logger.error(f"AgentPhaseManager for '{self.context.agent_id}': Notifier method '{notify_method_name}' not found or not callable on {type(self.notifier).__name__}.")

    @phase_transition(
        source_phases=[AgentOperationalPhase.SHUTDOWN_COMPLETE, AgentOperationalPhase.ERROR],
        target_phase=AgentOperationalPhase.UNINITIALIZED,
        description="Triggered when the agent runtime is started or restarted after being in a terminal state."
    )
    async def notify_runtime_starting_and_uninitialized(self) -> None:
        if self.context.current_phase == AgentOperationalPhase.UNINITIALIZED:
            await self._transition_phase(AgentOperationalPhase.UNINITIALIZED, "notify_phase_uninitialized_entered")
        elif self.context.current_phase.is_terminal():
             await self._transition_phase(AgentOperationalPhase.UNINITIALIZED, "notify_phase_uninitialized_entered")
        else:
             logger.warning(f"Agent '{self.context.agent_id}' notify_runtime_starting_and_uninitialized called in unexpected phase: {self.context.current_phase.value}")

    @phase_transition(
        source_phases=[AgentOperationalPhase.UNINITIALIZED],
        target_phase=AgentOperationalPhase.BOOTSTRAPPING,
        description="Occurs when the agent's internal bootstrapping process begins."
    )
    async def notify_bootstrapping_started(self) -> None:
        await self._transition_phase(AgentOperationalPhase.BOOTSTRAPPING, "notify_phase_bootstrapping_started")

    @phase_transition(
        source_phases=[AgentOperationalPhase.BOOTSTRAPPING],
        target_phase=AgentOperationalPhase.IDLE,
        description="Occurs when the agent successfully completes bootstrapping and is ready for input."
    )
    async def notify_initialization_complete(self) -> None:
        if self.context.current_phase.is_initializing() or self.context.current_phase == AgentOperationalPhase.UNINITIALIZED:
            # This will now be a BOOTSTRAPPING -> IDLE transition
            await self._transition_phase(AgentOperationalPhase.IDLE, "notify_phase_idle_entered")
        else:
            logger.warning(f"Agent '{self.context.agent_id}' notify_initialization_complete called in unexpected phase: {self.context.current_phase.value}")

    @phase_transition(
        source_phases=[
            AgentOperationalPhase.IDLE, AgentOperationalPhase.ANALYZING_LLM_RESPONSE,
            AgentOperationalPhase.PROCESSING_TOOL_RESULT, AgentOperationalPhase.EXECUTING_TOOL,
            AgentOperationalPhase.TOOL_DENIED
        ],
        target_phase=AgentOperationalPhase.PROCESSING_USER_INPUT,
        description="Fires when the agent begins processing a new user message or inter-agent message."
    )
    async def notify_processing_input_started(self, trigger_info: Optional[str] = None) -> None:
        if self.context.current_phase in [AgentOperationalPhase.IDLE, AgentOperationalPhase.ANALYZING_LLM_RESPONSE, AgentOperationalPhase.PROCESSING_TOOL_RESULT, AgentOperationalPhase.EXECUTING_TOOL, AgentOperationalPhase.TOOL_DENIED]:
            data = {"trigger_info": trigger_info} if trigger_info else {}
            await self._transition_phase(AgentOperationalPhase.PROCESSING_USER_INPUT, "notify_phase_processing_user_input_started", additional_data=data)
        elif self.context.current_phase == AgentOperationalPhase.PROCESSING_USER_INPUT:
             logger.debug(f"Agent '{self.context.agent_id}' already in PROCESSING_USER_INPUT phase.")
        else:
             logger.warning(f"Agent '{self.context.agent_id}' notify_processing_input_started called in unexpected phase: {self.context.current_phase.value}")

    @phase_transition(
        source_phases=[AgentOperationalPhase.PROCESSING_USER_INPUT, AgentOperationalPhase.PROCESSING_TOOL_RESULT],
        target_phase=AgentOperationalPhase.AWAITING_LLM_RESPONSE,
        description="Occurs just before the agent makes a call to the LLM."
    )
    async def notify_awaiting_llm_response(self) -> None:
        await self._transition_phase(AgentOperationalPhase.AWAITING_LLM_RESPONSE, "notify_phase_awaiting_llm_response_started")

    @phase_transition(
        source_phases=[AgentOperationalPhase.AWAITING_LLM_RESPONSE],
        target_phase=AgentOperationalPhase.ANALYZING_LLM_RESPONSE,
        description="Occurs after the agent has received a complete response from the LLM and begins to analyze it."
    )
    async def notify_analyzing_llm_response(self) -> None:
        await self._transition_phase(AgentOperationalPhase.ANALYZING_LLM_RESPONSE, "notify_phase_analyzing_llm_response_started")

    @phase_transition(
        source_phases=[AgentOperationalPhase.ANALYZING_LLM_RESPONSE],
        target_phase=AgentOperationalPhase.AWAITING_TOOL_APPROVAL,
        description="Occurs if the agent proposes a tool use that requires manual user approval."
    )
    async def notify_tool_execution_pending_approval(self, tool_invocation: 'ToolInvocation') -> None:
        await self._transition_phase(AgentOperationalPhase.AWAITING_TOOL_APPROVAL, "notify_phase_awaiting_tool_approval_started")

    @phase_transition(
        source_phases=[AgentOperationalPhase.AWAITING_TOOL_APPROVAL],
        target_phase=AgentOperationalPhase.EXECUTING_TOOL,
        description="Occurs after a pending tool use has been approved and is about to be executed."
    )
    async def notify_tool_execution_resumed_after_approval(self, approved: bool, tool_name: Optional[str]) -> None:
        if approved and tool_name:
            await self._transition_phase(AgentOperationalPhase.EXECUTING_TOOL, "notify_phase_executing_tool_started", additional_data={"tool_name": tool_name})
        else:
            logger.info(f"Agent '{self.context.agent_id}' tool execution denied for '{tool_name}'. Transitioning to allow LLM to process denial.")
            await self.notify_tool_denied(tool_name)

    @phase_transition(
        source_phases=[AgentOperationalPhase.AWAITING_TOOL_APPROVAL],
        target_phase=AgentOperationalPhase.TOOL_DENIED,
        description="Occurs after a pending tool use has been denied by the user."
    )
    async def notify_tool_denied(self, tool_name: Optional[str]) -> None:
        """Notifies that a tool execution has been denied."""
        await self._transition_phase(
            AgentOperationalPhase.TOOL_DENIED,
            "notify_phase_tool_denied_started",
            additional_data={"tool_name": tool_name, "denial_for_tool": tool_name}
        )

    @phase_transition(
        source_phases=[AgentOperationalPhase.ANALYZING_LLM_RESPONSE],
        target_phase=AgentOperationalPhase.EXECUTING_TOOL,
        description="Occurs when an agent with auto-approval executes a tool."
    )
    async def notify_tool_execution_started(self, tool_name: str) -> None:
        await self._transition_phase(AgentOperationalPhase.EXECUTING_TOOL, "notify_phase_executing_tool_started", additional_data={"tool_name": tool_name})

    @phase_transition(
        source_phases=[AgentOperationalPhase.EXECUTING_TOOL],
        target_phase=AgentOperationalPhase.PROCESSING_TOOL_RESULT,
        description="Fires after a tool has finished executing and the agent begins processing its result."
    )
    async def notify_processing_tool_result(self, tool_name: str) -> None:
        await self._transition_phase(AgentOperationalPhase.PROCESSING_TOOL_RESULT, "notify_phase_processing_tool_result_started", additional_data={"tool_name": tool_name})

    @phase_transition(
        source_phases=[
            AgentOperationalPhase.PROCESSING_USER_INPUT, AgentOperationalPhase.ANALYZING_LLM_RESPONSE,
            AgentOperationalPhase.PROCESSING_TOOL_RESULT
        ],
        target_phase=AgentOperationalPhase.IDLE,
        description="Occurs when an agent completes a processing cycle and is waiting for new input."
    )
    async def notify_processing_complete_and_idle(self) -> None:
        if not self.context.current_phase.is_terminal() and self.context.current_phase != AgentOperationalPhase.IDLE:
            await self._transition_phase(AgentOperationalPhase.IDLE, "notify_phase_idle_entered")
        elif self.context.current_phase == AgentOperationalPhase.IDLE:
            logger.debug(f"Agent '{self.context.agent_id}' processing complete, already IDLE.")
        else:
            logger.warning(f"Agent '{self.context.agent_id}' notify_processing_complete_and_idle called in unexpected phase: {self.context.current_phase.value}")

    @phase_transition(
        source_phases=[
            AgentOperationalPhase.UNINITIALIZED, AgentOperationalPhase.BOOTSTRAPPING, AgentOperationalPhase.IDLE,
            AgentOperationalPhase.PROCESSING_USER_INPUT, AgentOperationalPhase.AWAITING_LLM_RESPONSE,
            AgentOperationalPhase.ANALYZING_LLM_RESPONSE, AgentOperationalPhase.AWAITING_TOOL_APPROVAL,
            AgentOperationalPhase.TOOL_DENIED, AgentOperationalPhase.EXECUTING_TOOL,
            AgentOperationalPhase.PROCESSING_TOOL_RESULT, AgentOperationalPhase.SHUTTING_DOWN
        ],
        target_phase=AgentOperationalPhase.ERROR,
        description="A catch-all transition that can occur from any non-terminal state if an unrecoverable error happens."
    )
    async def notify_error_occurred(self, error_message: str, error_details: Optional[str] = None) -> None:
        if self.context.current_phase != AgentOperationalPhase.ERROR:
            data = {"error_message": error_message, "error_details": error_details}
            await self._transition_phase(AgentOperationalPhase.ERROR, "notify_phase_error_entered", additional_data=data)
        else:
            logger.debug(f"Agent '{self.context.agent_id}' already in ERROR phase when another error notified: {error_message}")

    @phase_transition(
        source_phases=[
            AgentOperationalPhase.UNINITIALIZED, AgentOperationalPhase.BOOTSTRAPPING, AgentOperationalPhase.IDLE,
            AgentOperationalPhase.PROCESSING_USER_INPUT, AgentOperationalPhase.AWAITING_LLM_RESPONSE,
            AgentOperationalPhase.ANALYZING_LLM_RESPONSE, AgentOperationalPhase.AWAITING_TOOL_APPROVAL,
            AgentOperationalPhase.TOOL_DENIED, AgentOperationalPhase.EXECUTING_TOOL,
            AgentOperationalPhase.PROCESSING_TOOL_RESULT
        ],
        target_phase=AgentOperationalPhase.SHUTTING_DOWN,
        description="Fires when the agent begins its graceful shutdown sequence."
    )
    async def notify_shutdown_initiated(self) -> None:
        if not self.context.current_phase.is_terminal():
             await self._transition_phase(AgentOperationalPhase.SHUTTING_DOWN, "notify_phase_shutting_down_started")
        else:
            logger.debug(f"Agent '{self.context.agent_id}' shutdown initiated but already in a terminal phase: {self.context.current_phase.value}")

    @phase_transition(
        source_phases=[AgentOperationalPhase.SHUTTING_DOWN],
        target_phase=AgentOperationalPhase.SHUTDOWN_COMPLETE,
        description="The final transition when the agent has successfully shut down and released its resources."
    )
    async def notify_final_shutdown_complete(self) -> None:
        final_phase = AgentOperationalPhase.ERROR if self.context.current_phase == AgentOperationalPhase.ERROR else AgentOperationalPhase.SHUTDOWN_COMPLETE
        if final_phase == AgentOperationalPhase.ERROR:
            await self._transition_phase(AgentOperationalPhase.ERROR, "notify_phase_error_entered", additional_data={"error_message": "Shutdown completed with agent in error state."})
        else:
            await self._transition_phase(AgentOperationalPhase.SHUTDOWN_COMPLETE, "notify_phase_shutdown_completed")
