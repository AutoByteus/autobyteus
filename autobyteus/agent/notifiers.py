# file: autobyteus/autobyteus/agent/notifiers.py
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType
from autobyteus.agent.phases import AgentOperationalPhase

if TYPE_CHECKING:
    pass 

logger = logging.getLogger(__name__)

class AgentExternalEventNotifier(EventEmitter):
    """
    Responsible for emitting external events related to agent phase transitions.
    It is used by AgentPhaseManager. Phase events are lean signals.
    """
    def __init__(self, agent_id: str):
        super().__init__()
        self.agent_id: str = agent_id
        logger.debug(f"AgentExternalEventNotifier initialized for agent_id '{self.agent_id}'.")

    def _emit_phase_change(self, 
                           event_type: EventType, 
                           new_phase: AgentOperationalPhase,
                           old_phase: Optional[AgentOperationalPhase] = None, 
                           additional_data: Optional[Dict[str, Any]] = None):
        """Helper to emit phase change events with a standard payload structure."""
        payload = {
            "agent_id": self.agent_id,
            "new_phase": new_phase.value,
            "old_phase": old_phase.value if old_phase else None,
        }
        if additional_data: 
            payload.update(additional_data)
        
        self.emit(event_type, **payload)
        logger.info(f"AgentExternalEventNotifier for '{self.agent_id}' emitted {event_type.name} (New Phase: {new_phase.value}). Payload keys: {list(payload.keys())}")

    def notify_phase_uninitialized_entered(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_UNINITIALIZED_ENTERED, AgentOperationalPhase.UNINITIALIZED, old_phase)

    def notify_phase_initializing_tools_started(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_INITIALIZING_TOOLS_STARTED, AgentOperationalPhase.INITIALIZING_TOOLS, old_phase)

    def notify_phase_initializing_prompt_started(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_INITIALIZING_PROMPT_STARTED, AgentOperationalPhase.INITIALIZING_PROMPT, old_phase)

    def notify_phase_initializing_llm_started(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_INITIALIZING_LLM_STARTED, AgentOperationalPhase.INITIALIZING_LLM, old_phase)

    def notify_phase_idle_entered(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_IDLE_ENTERED, AgentOperationalPhase.IDLE, old_phase)
 
    def notify_phase_processing_user_input_started(self, old_phase: Optional[AgentOperationalPhase], trigger_info: Optional[str] = None):
        data = {"trigger": trigger_info} if trigger_info else {}
        self._emit_phase_change(EventType.AGENT_PHASE_PROCESSING_USER_INPUT_STARTED, AgentOperationalPhase.PROCESSING_USER_INPUT, old_phase, additional_data=data)

    def notify_phase_awaiting_llm_response_started(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_AWAITING_LLM_RESPONSE_STARTED, AgentOperationalPhase.AWAITING_LLM_RESPONSE, old_phase)
    
    def notify_phase_analyzing_llm_response_started(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_ANALYZING_LLM_RESPONSE_STARTED, AgentOperationalPhase.ANALYZING_LLM_RESPONSE, old_phase)

    def notify_phase_awaiting_tool_approval_started(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_AWAITING_TOOL_APPROVAL_STARTED, 
                                AgentOperationalPhase.AWAITING_TOOL_APPROVAL, 
                                old_phase)

    def notify_phase_executing_tool_started(self, old_phase: Optional[AgentOperationalPhase], tool_name: str):
        data = {"tool_name": tool_name}
        self._emit_phase_change(EventType.AGENT_PHASE_EXECUTING_TOOL_STARTED, AgentOperationalPhase.EXECUTING_TOOL, old_phase, additional_data=data)

    def notify_phase_processing_tool_result_started(self, old_phase: Optional[AgentOperationalPhase], tool_name: str):
        data = {"tool_name": tool_name}
        self._emit_phase_change(EventType.AGENT_PHASE_PROCESSING_TOOL_RESULT_STARTED, AgentOperationalPhase.PROCESSING_TOOL_RESULT, old_phase, additional_data=data)

    def notify_phase_shutting_down_started(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_SHUTTING_DOWN_STARTED, AgentOperationalPhase.SHUTTING_DOWN, old_phase)

    def notify_phase_shutdown_completed(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_SHUTDOWN_COMPLETED, AgentOperationalPhase.SHUTDOWN_COMPLETE, old_phase)

    def notify_phase_error_entered(self, old_phase: Optional[AgentOperationalPhase], error_message: str, error_details: Optional[str] = None):
        data = {"error_message": error_message, "error_details": error_details}
        self._emit_phase_change(EventType.AGENT_PHASE_ERROR_ENTERED, AgentOperationalPhase.ERROR, old_phase, additional_data=data)
