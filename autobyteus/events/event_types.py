# file: autobyteus/autobyteus/events/event_types.py
from enum import Enum

class EventType(Enum): 
    """
    Defines the types of events that can be emitted by EventEmitters within the system.
    Uses prefixes like AGENT_STATUS_, AGENT_DATA_, AGENT_REQUEST_, AGENT_ERROR_ for clarity.
    """
    # --- Non-Agent specific events ---
    WEIBO_POST_COMPLETED = "weibo_post_completed" # Example, keep as is
    TOOL_EXECUTION_COMPLETED = "tool_execution_completed" # Added for generic tool events
    SHARED_BROWSER_SESSION_CREATED = "shared_browser_session_created" # Added for session-aware tools
    CREATE_SHARED_SESSION = "create_shared_session" # Added for session-aware tools

    # --- Agent Status Updates ---
    AGENT_STATUS_UPDATED = "agent_status_updated"

    # --- Agent Data Outputs ---
    AGENT_DATA_ASSISTANT_CHUNK = "agent_data_assistant_chunk" 
    AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE = "agent_data_assistant_complete_response"
    AGENT_DATA_SEGMENT_EVENT = "agent_data_segment_event"  # Streaming parser segment events
    AGENT_DATA_TOOL_LOG = "agent_data_tool_log" 
    AGENT_DATA_TOOL_LOG_STREAM_END = "agent_data_tool_log_stream_end" 
    AGENT_DATA_SYSTEM_TASK_NOTIFICATION_RECEIVED = "agent_data_system_task_notification_received" # NEW
    AGENT_DATA_INTER_AGENT_MESSAGE_RECEIVED = "agent_data_inter_agent_message_received"  # NEW: surface inter-agent messages
    AGENT_DATA_TODO_LIST_UPDATED = "agent_data_todo_list_updated"
    AGENT_ARTIFACT_PERSISTED = "agent_artifact_persisted" # NEW: artifact persistence confirmation
    AGENT_ARTIFACT_UPDATED = "agent_artifact_updated" # NEW: artifact content updated (e.g., patch_file)
    
    # --- Agent Requests for External Interaction ---
    AGENT_REQUEST_TOOL_INVOCATION_APPROVAL = "agent_request_tool_invocation_approval" 
    AGENT_TOOL_INVOCATION_AUTO_EXECUTING = "agent_tool_invocation_auto_executing"
    
    # --- Agent Errors (not necessarily status changes, e.g., error during output generation) ---
    AGENT_ERROR_OUTPUT_GENERATION = "agent_error_output_generation"

    # --- Agent Team Events ---
    TEAM_STREAM_EVENT = "team_stream_event" # For unified agent team event stream

    # --- Workflow Events ---
    WORKFLOW_STREAM_EVENT = "workflow_stream_event" # For unified workflow event stream

    # --- Task Plan Events ---
    TASK_PLAN_TASKS_CREATED = "task_plan.tasks.created"
    TASK_PLAN_STATUS_UPDATED = "task_plan.status.updated"

    def __str__(self): 
        return self.value
