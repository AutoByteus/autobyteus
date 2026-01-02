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
    Responsible for emitting external events related to agent status updates
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


    def _emit_status_update(self,
                            new_status: AgentStatus,
                            old_status: Optional[AgentStatus] = None,
                            additional_data: Optional[Dict[str, Any]] = None):
        status_payload_dict = { 
            "new_status": new_status.value, 
            "old_status": old_status.value if old_status else None,
        }
        if additional_data: 
            status_payload_dict.update(additional_data)
        self._emit_event(EventType.AGENT_STATUS_UPDATED, payload_content=status_payload_dict)

    def notify_status_updated(self,
                              new_status: AgentStatus,
                              old_status: Optional[AgentStatus] = None,
                              additional_data: Optional[Dict[str, Any]] = None):
        self._emit_status_update(new_status, old_status, additional_data)

    def notify_agent_data_assistant_chunk(self, chunk: 'ChunkResponse'): 
        self._emit_event(EventType.AGENT_DATA_ASSISTANT_CHUNK, payload_content=chunk) 

    def notify_agent_data_assistant_chunk_stream_end(self): 
        self._emit_event(EventType.AGENT_DATA_ASSISTANT_CHUNK_STREAM_END) 

    def notify_agent_data_assistant_complete_response(self, complete_response: 'CompleteResponse'):
        self._emit_event(EventType.AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE, payload_content=complete_response) 

    def notify_agent_segment_event(self, event_dict: Dict[str, Any]):
        """Notify a streaming parser segment event (START, CONTENT, END)."""
        self._emit_event(EventType.AGENT_DATA_SEGMENT_EVENT, payload_content=event_dict)

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
