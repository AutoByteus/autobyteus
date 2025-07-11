# file: autobyteus/autobyteus/agent/streaming/stream_event_payloads.py
import logging
from typing import Dict, Any, Optional, List, Union 
from pydantic import BaseModel, Field

from autobyteus.llm.utils.token_usage import TokenUsage 
from autobyteus.agent.phases import AgentOperationalPhase


logger = logging.getLogger(__name__)

# --- Base Payload Model (Optional, for common fields if any) ---
class BaseStreamPayload(BaseModel):
    pass

# --- Specific Payload Models for each StreamEventType ---

class AssistantChunkData(BaseStreamPayload):
    content: str
    reasoning: Optional[str] = None
    is_complete: bool
    usage: Optional[TokenUsage] = None 


class AssistantCompleteResponseData(BaseStreamPayload):
    content: str
    reasoning: Optional[str] = None
    usage: Optional[TokenUsage] = None 

class ToolInteractionLogEntryData(BaseStreamPayload):
    log_entry: str
    tool_invocation_id: str
    tool_name: str

class AgentOperationalPhaseTransitionData(BaseStreamPayload): 
    new_phase: AgentOperationalPhase 
    old_phase: Optional[AgentOperationalPhase] = None
    trigger: Optional[str] = None
    tool_name: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None

class ErrorEventData(BaseStreamPayload):
    source: str
    message: str
    details: Optional[str] = None

class ToolInvocationApprovalRequestedData(BaseStreamPayload):
    invocation_id: str
    tool_name: str
    arguments: Dict[str, Any]

class ToolInvocationAutoExecutingData(BaseStreamPayload):
    invocation_id: str
    tool_name: str
    arguments: Dict[str, Any]

class EmptyData(BaseStreamPayload):
    pass

# Union of all possible data payload types
StreamDataPayload = Union[
    AssistantChunkData,
    AssistantCompleteResponseData, 
    ToolInteractionLogEntryData,
    AgentOperationalPhaseTransitionData, 
    ErrorEventData,
    ToolInvocationApprovalRequestedData,
    ToolInvocationAutoExecutingData,
    EmptyData
]

# Factory functions to create payload models from various inputs

def create_assistant_chunk_data(chunk_obj: Any) -> AssistantChunkData:
    usage_data = None
    if hasattr(chunk_obj, 'usage'):
        usage_data = getattr(chunk_obj, 'usage')
    elif isinstance(chunk_obj, dict) and 'usage' in chunk_obj:
        usage_data = chunk_obj.get('usage')

    parsed_usage = None
    if usage_data:
        if isinstance(usage_data, TokenUsage):
            parsed_usage = usage_data
        elif isinstance(usage_data, dict):
            try:
                parsed_usage = TokenUsage(**usage_data)
            except Exception as e:
                logger.warning(f"Could not parse usage dict into TokenUsage for AssistantChunkData: {e}. Usage dict: {usage_data}")
        else:
            logger.warning(f"Unsupported usage type {type(usage_data)} for AssistantChunkData.")

    if hasattr(chunk_obj, 'content') and hasattr(chunk_obj, 'is_complete'):
        return AssistantChunkData(
            content=str(getattr(chunk_obj, 'content', '')),
            reasoning=getattr(chunk_obj, 'reasoning', None),
            is_complete=bool(getattr(chunk_obj, 'is_complete', False)),
            usage=parsed_usage
        )
    elif isinstance(chunk_obj, dict): 
         return AssistantChunkData(
            content=str(chunk_obj.get('content', '')),
            reasoning=chunk_obj.get('reasoning', None),
            is_complete=bool(chunk_obj.get('is_complete', False)),
            usage=parsed_usage
        )
    raise ValueError(f"Cannot create AssistantChunkData from {type(chunk_obj)}")

def create_assistant_complete_response_data(complete_resp_obj: Any) -> AssistantCompleteResponseData:
    usage_data = None
    if hasattr(complete_resp_obj, 'usage'):
        usage_data = getattr(complete_resp_obj, 'usage')
    elif isinstance(complete_resp_obj, dict) and 'usage' in complete_resp_obj:
        usage_data = complete_resp_obj.get('usage')
    
    parsed_usage = None
    if usage_data:
        if isinstance(usage_data, TokenUsage):
            parsed_usage = usage_data
        elif isinstance(usage_data, dict):
            try:
                parsed_usage = TokenUsage(**usage_data)
            except Exception as e: # pragma: no cover
                logger.warning(f"Could not parse usage dict into TokenUsage for AssistantCompleteResponseData: {e}. Usage dict: {usage_data}")
        else: # pragma: no cover
            logger.warning(f"Unsupported usage type {type(usage_data)} for AssistantCompleteResponseData.")

    if hasattr(complete_resp_obj, 'content'):
        return AssistantCompleteResponseData(
            content=str(getattr(complete_resp_obj, 'content', '')),
            reasoning=getattr(complete_resp_obj, 'reasoning', None),
            usage=parsed_usage
        )
    elif isinstance(complete_resp_obj, dict): 
        return AssistantCompleteResponseData(
            content=str(complete_resp_obj.get('content', '')),
            reasoning=complete_resp_obj.get('reasoning', None),
            usage=parsed_usage
        )
    raise ValueError(f"Cannot create AssistantCompleteResponseData from {type(complete_resp_obj)}")

def create_tool_interaction_log_entry_data(log_data: Any) -> ToolInteractionLogEntryData:
    if isinstance(log_data, dict):
        if all(k in log_data for k in ['log_entry', 'tool_invocation_id', 'tool_name']):
            return ToolInteractionLogEntryData(**log_data)
    raise ValueError(f"Cannot create ToolInteractionLogEntryData from {type(log_data)}. Expected dict with 'log_entry', 'tool_invocation_id', and 'tool_name' keys.")

def create_agent_operational_phase_transition_data(phase_data_dict: Any) -> AgentOperationalPhaseTransitionData: 
    if isinstance(phase_data_dict, dict):
        return AgentOperationalPhaseTransitionData(**phase_data_dict) 
    raise ValueError(f"Cannot create AgentOperationalPhaseTransitionData from {type(phase_data_dict)}") 

def create_error_event_data(error_data_dict: Any) -> ErrorEventData:
    if isinstance(error_data_dict, dict):
        return ErrorEventData(**error_data_dict)
    raise ValueError(f"Cannot create ErrorEventData from {type(error_data_dict)}")

def create_tool_invocation_approval_requested_data(approval_data_dict: Any) -> ToolInvocationApprovalRequestedData:
    if isinstance(approval_data_dict, dict):
        return ToolInvocationApprovalRequestedData(**approval_data_dict)
    raise ValueError(f"Cannot create ToolInvocationApprovalRequestedData from {type(approval_data_dict)}")

def create_tool_invocation_auto_executing_data(auto_exec_data_dict: Any) -> ToolInvocationAutoExecutingData:
    if isinstance(auto_exec_data_dict, dict):
        return ToolInvocationAutoExecutingData(**auto_exec_data_dict)
    raise ValueError(f"Cannot create ToolInvocationAutoExecutingData from {type(auto_exec_data_dict)}")
