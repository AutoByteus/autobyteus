# file: autobyteus/autobyteus/agent/events/notifiers.py
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType 
from autobyteus.agent.phases import AgentOperationalPhase

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse 

logger = logging.getLogger(__name__)

class AgentExternalEventNotifier(EventEmitter):
    """
    Responsible for emitting external events related to agent phase transitions
    and data outputs.
    """
    def __init__(self, agent_id: str):
        super().__init__()
        self.agent_id: str = agent_id
        logger.debug(f"AgentExternalEventNotifier initialized for agent_id '{self.agent_id}' (NotifierID: {self.object_id}).")

    def _emit_event(self, event_type: EventType, payload_content: Optional[Any] = None): 
        emit_kwargs: Dict[str, Any] = {"agent_id": self.agent_id}
        if payload_content is not None:
            emit_kwargs["payload"] = payload_content 
        
        self.emit(event_type, **emit_kwargs) 
        log_message = (
            f"AgentExternalEventNotifier (NotifierID: {self.object_id}, AgentID: {self.agent_id}) "
            f"emitted {event_type.name}. Kwarg keys for emit: {list(emit_kwargs.keys())}"
        )
        # Reduce log level for high-frequency events like streaming chunks
        if event_type == EventType.AGENT_DATA_ASSISTANT_CHUNK:
            logger.debug(log_message)
        else:
            logger.info(log_message)


    def _emit_phase_change(self, 
                           event_type: EventType, 
                           new_phase: AgentOperationalPhase,
                           old_phase: Optional[AgentOperationalPhase] = None, 
                           additional_data: Optional[Dict[str, Any]] = None):
        phase_payload_dict = { 
            "new_phase": new_phase.value, 
            "old_phase": old_phase.value if old_phase else None,
        }
        if additional_data: 
            phase_payload_dict.update(additional_data)
        self._emit_event(event_type, payload_content=phase_payload_dict) 

    def notify_phase_uninitialized_entered(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_UNINITIALIZED_ENTERED, AgentOperationalPhase.UNINITIALIZED, old_phase)

    def notify_phase_bootstrapping_started(self, old_phase: Optional[AgentOperationalPhase]):
        self._emit_phase_change(EventType.AGENT_PHASE_BOOTSTRAPPING_STARTED, AgentOperationalPhase.BOOTSTRAPPING, old_phase)

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
        self._emit_phase_change(EventType.AGENT_PHASE_AWAITING_TOOL_APPROVAL_STARTED, AgentOperationalPhase.AWAITING_TOOL_APPROVAL, old_phase)

    def notify_phase_tool_denied_started(self, old_phase: Optional[AgentOperationalPhase], tool_name: Optional[str], denial_for_tool: Optional[str]):
        data = {"tool_name": tool_name, "denial_for_tool": denial_for_tool}
        # Assuming EventType.AGENT_PHASE_TOOL_DENIED_STARTED exists in the main EventType enum
        self._emit_phase_change(EventType.AGENT_PHASE_TOOL_DENIED_STARTED, AgentOperationalPhase.TOOL_DENIED, old_phase, additional_data=data)

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

    def notify_agent_data_assistant_chunk(self, chunk: 'ChunkResponse'): 
        self._emit_event(EventType.AGENT_DATA_ASSISTANT_CHUNK, payload_content=chunk) 

    def notify_agent_data_assistant_chunk_stream_end(self): 
        self._emit_event(EventType.AGENT_DATA_ASSISTANT_CHUNK_STREAM_END) 

    def notify_agent_data_assistant_complete_response(self, complete_response: 'CompleteResponse'):
        self._emit_event(EventType.AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE, payload_content=complete_response) 

    def notify_agent_data_tool_log(self, log_data: Dict[str, Any]): 
        self._emit_event(EventType.AGENT_DATA_TOOL_LOG, payload_content=log_data) 
    
    def notify_agent_data_tool_log_stream_end(self): 
        self._emit_event(EventType.AGENT_DATA_TOOL_LOG_STREAM_END) 
    
    def notify_agent_request_tool_invocation_approval(self, approval_data: Dict[str, Any]): 
        self._emit_event(EventType.AGENT_REQUEST_TOOL_INVOCATION_APPROVAL, payload_content=approval_data) 

    def notify_agent_tool_invocation_auto_executing(self, auto_exec_data: Dict[str, Any]):
        """Notifies that a tool is being automatically executed."""
        self._emit_event(EventType.AGENT_TOOL_INVOCATION_AUTO_EXECUTING, payload_content=auto_exec_data)

    def notify_agent_error_output_generation(self, error_source: str, error_message: str, error_details: Optional[str] = None): 
        payload_dict = { 
            "source": error_source,
            "message": error_message,
            "details": error_details
        }
        self._emit_event(EventType.AGENT_ERROR_OUTPUT_GENERATION, payload_content=payload_dict)
