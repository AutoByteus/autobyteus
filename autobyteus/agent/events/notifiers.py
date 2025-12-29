# file: autobyteus/autobyteus/agent/events/notifiers.py
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING, List

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType 
from autobyteus.agent.status.status_enum import AgentStatus

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse 

logger = logging.getLogger(__name__)

class AgentExternalEventNotifier(EventEmitter):
    """
    Responsible for emitting external events related to agent status transitions
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


    def _emit_status_change(self, 
                           event_type: EventType, 
                           new_status: AgentStatus,
                           old_status: Optional[AgentStatus] = None, 
                           additional_data: Optional[Dict[str, Any]] = None):
        status_payload_dict = { 
            "new_status": new_status.value, 
            "old_status": old_status.value if old_status else None,
        }
        if additional_data: 
            status_payload_dict.update(additional_data)
        self._emit_event(event_type, payload_content=status_payload_dict) 

    def notify_status_uninitialized_entered(self, old_status: Optional[AgentStatus]):
        self._emit_status_change(EventType.AGENT_STATUS_UNINITIALIZED_ENTERED, AgentStatus.UNINITIALIZED, old_status)

    def notify_status_bootstrapping_started(self, old_status: Optional[AgentStatus]):
        self._emit_status_change(EventType.AGENT_STATUS_BOOTSTRAPPING_STARTED, AgentStatus.BOOTSTRAPPING, old_status)

    def notify_status_idle_entered(self, old_status: Optional[AgentStatus]):
        self._emit_status_change(EventType.AGENT_STATUS_IDLE_ENTERED, AgentStatus.IDLE, old_status)

    def notify_status_processing_user_input_started(self, old_status: Optional[AgentStatus], trigger_info: Optional[str] = None):
        data = {"trigger": trigger_info} if trigger_info else {}
        self._emit_status_change(EventType.AGENT_STATUS_PROCESSING_USER_INPUT_STARTED, AgentStatus.PROCESSING_USER_INPUT, old_status, additional_data=data)
    def notify_status_awaiting_llm_response_started(self, old_status: Optional[AgentStatus]):
        self._emit_status_change(EventType.AGENT_STATUS_AWAITING_LLM_RESPONSE_STARTED, AgentStatus.AWAITING_LLM_RESPONSE, old_status)

    def notify_status_analyzing_llm_response_started(self, old_status: Optional[AgentStatus]):
        self._emit_status_change(EventType.AGENT_STATUS_ANALYZING_LLM_RESPONSE_STARTED, AgentStatus.ANALYZING_LLM_RESPONSE, old_status)

    def notify_status_awaiting_tool_approval_started(self, old_status: Optional[AgentStatus]):
        self._emit_status_change(EventType.AGENT_STATUS_AWAITING_TOOL_APPROVAL_STARTED, AgentStatus.AWAITING_TOOL_APPROVAL, old_status)

    def notify_status_tool_denied_started(self, old_status: Optional[AgentStatus], tool_name: Optional[str], denial_for_tool: Optional[str]):
        data = {"tool_name": tool_name, "denial_for_tool": denial_for_tool}
        # Assuming EventType.AGENT_STATUS_TOOL_DENIED_STARTED exists in the main EventType enum
        self._emit_status_change(EventType.AGENT_STATUS_TOOL_DENIED_STARTED, AgentStatus.TOOL_DENIED, old_status, additional_data=data)

    def notify_status_executing_tool_started(self, old_status: Optional[AgentStatus], tool_name: str):
        data = {"tool_name": tool_name}
        self._emit_status_change(EventType.AGENT_STATUS_EXECUTING_TOOL_STARTED, AgentStatus.EXECUTING_TOOL, old_status, additional_data=data)
    def notify_status_processing_tool_result_started(self, old_status: Optional[AgentStatus], tool_name: str):
        data = {"tool_name": tool_name}
        self._emit_status_change(EventType.AGENT_STATUS_PROCESSING_TOOL_RESULT_STARTED, AgentStatus.PROCESSING_TOOL_RESULT, old_status, additional_data=data)
    def notify_status_shutting_down_started(self, old_status: Optional[AgentStatus]):
        self._emit_status_change(EventType.AGENT_STATUS_SHUTTING_DOWN_STARTED, AgentStatus.SHUTTING_DOWN, old_status)
    def notify_status_shutdown_completed(self, old_status: Optional[AgentStatus]):
        self._emit_status_change(EventType.AGENT_STATUS_SHUTDOWN_COMPLETED, AgentStatus.SHUTDOWN_COMPLETE, old_status)
    def notify_status_error_entered(self, old_status: Optional[AgentStatus], error_message: str, error_details: Optional[str] = None):
        data = {"error_message": error_message, "error_details": error_details}
        self._emit_status_change(EventType.AGENT_STATUS_ERROR_ENTERED, AgentStatus.ERROR, old_status, additional_data=data)

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
        
    def notify_agent_data_system_task_notification_received(self, notification_data: Dict[str, Any]):
        """Notifies that the agent has received a system-generated task notification."""
        self._emit_event(EventType.AGENT_DATA_SYSTEM_TASK_NOTIFICATION_RECEIVED, payload_content=notification_data)

    def notify_agent_data_inter_agent_message_received(self, message_data: Dict[str, Any]):
        """Notifies that the agent has received a message from another agent."""
        self._emit_event(EventType.AGENT_DATA_INTER_AGENT_MESSAGE_RECEIVED, payload_content=message_data)

    def notify_agent_data_todo_list_updated(self, todo_list: List[Dict[str, Any]]):
        """Notifies that the agent's ToDo list has been updated."""
        self._emit_event(EventType.AGENT_DATA_TODO_LIST_UPDATED, payload_content={"todos": todo_list})

    def notify_agent_error_output_generation(self, error_source: str, error_message: str, error_details: Optional[str] = None): 
        payload_dict = { 
            "source": error_source,
            "message": error_message,
            "details": error_details
        }
        self._emit_event(EventType.AGENT_ERROR_OUTPUT_GENERATION, payload_content=payload_dict)
