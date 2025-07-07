# file: autobyteus/autobyteus/events/event_types.py
from enum import Enum

class EventType(Enum): 
    """
    Defines the types of events that can be emitted by EventEmitters within the system.
    Uses prefixes like AGENT_PHASE_, AGENT_DATA_, AGENT_REQUEST_, AGENT_ERROR_ for clarity.
    """
    # --- Non-Agent specific events ---
    WEIBO_POST_COMPLETED = "weibo_post_completed" # Example, keep as is
    TOOL_EXECUTION_COMPLETED = "tool_execution_completed" # Added for generic tool events
    TIMER_UPDATE = "timer_update" # Added for Timer tool
    SHARED_BROWSER_SESSION_CREATED = "shared_browser_session_created" # Added for session-aware tools
    CREATE_SHARED_SESSION = "create_shared_session" # Added for session-aware tools

    # --- Agent Phase Transitions ---
    AGENT_PHASE_UNINITIALIZED_ENTERED = "agent_phase_uninitialized_entered"
    AGENT_PHASE_BOOTSTRAPPING_STARTED = "agent_phase_bootstrapping_started"
    AGENT_PHASE_IDLE_ENTERED = "agent_phase_idle_entered"
    AGENT_PHASE_PROCESSING_USER_INPUT_STARTED = "agent_phase_processing_user_input_started"
    AGENT_PHASE_AWAITING_LLM_RESPONSE_STARTED = "agent_phase_awaiting_llm_response_started"
    AGENT_PHASE_ANALYZING_LLM_RESPONSE_STARTED = "agent_phase_analyzing_llm_response_started"
    AGENT_PHASE_AWAITING_TOOL_APPROVAL_STARTED = "agent_phase_awaiting_tool_approval_started" 
    AGENT_PHASE_TOOL_DENIED_STARTED = "agent_phase_tool_denied_started"
    AGENT_PHASE_EXECUTING_TOOL_STARTED = "agent_phase_executing_tool_started"
    AGENT_PHASE_PROCESSING_TOOL_RESULT_STARTED = "agent_phase_processing_tool_result_started"
    AGENT_PHASE_SHUTTING_DOWN_STARTED = "agent_phase_shutting_down_started"
    AGENT_PHASE_SHUTDOWN_COMPLETED = "agent_phase_shutdown_completed"
    AGENT_PHASE_ERROR_ENTERED = "agent_phase_error_entered" 

    # --- Agent Data Outputs ---
    AGENT_DATA_ASSISTANT_CHUNK = "agent_data_assistant_chunk" 
    AGENT_DATA_ASSISTANT_CHUNK_STREAM_END = "agent_data_assistant_chunk_stream_end" 
    AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE = "agent_data_assistant_complete_response"
    AGENT_DATA_TOOL_LOG = "agent_data_tool_log" 
    AGENT_DATA_TOOL_LOG_STREAM_END = "agent_data_tool_log_stream_end" 
    
    # --- Agent Requests for External Interaction ---
    AGENT_REQUEST_TOOL_INVOCATION_APPROVAL = "agent_request_tool_invocation_approval" 
    AGENT_TOOL_INVOCATION_AUTO_EXECUTING = "agent_tool_invocation_auto_executing"
    
    # --- Agent Errors (not necessarily phase changes, e.g., error during output generation) ---
    AGENT_ERROR_OUTPUT_GENERATION = "agent_error_output_generation"

    def __str__(self): 
        return self.value
