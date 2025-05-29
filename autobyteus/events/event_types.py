# file: autobyteus/autobyteus/events/event_types.py
from enum import Enum

class EventType(Enum):
    """
    Defines the types of events that can be emitted by EventEmitters within the system.
    These are typically for internal or inter-component communication.
    External-facing events for clients are usually via StreamEventType in AgentEventStream.
    """
    WEIBO_POST_COMPLETED = "weibo_post_completed"

    # --- Agent Operational Phase Transitions (Primary external signals) ---
    AGENT_PHASE_UNINITIALIZED_ENTERED = "agent_phase_uninitialized_entered"
    AGENT_PHASE_INITIALIZING_TOOLS_STARTED = "agent_phase_initializing_tools_started"
    AGENT_PHASE_INITIALIZING_PROMPT_STARTED = "agent_phase_initializing_prompt_started"
    AGENT_PHASE_INITIALIZING_LLM_STARTED = "agent_phase_initializing_llm_started"
    AGENT_PHASE_IDLE_ENTERED = "agent_phase_idle_entered"
    
    AGENT_PHASE_PROCESSING_USER_INPUT_STARTED = "agent_phase_processing_user_input_started"
    AGENT_PHASE_AWAITING_LLM_RESPONSE_STARTED = "agent_phase_awaiting_llm_response_started"
    AGENT_PHASE_ANALYZING_LLM_RESPONSE_STARTED = "agent_phase_analyzing_llm_response_started"
    
    AGENT_PHASE_AWAITING_TOOL_APPROVAL_STARTED = "agent_phase_awaiting_tool_approval_started" 
    
    AGENT_PHASE_EXECUTING_TOOL_STARTED = "agent_phase_executing_tool_started"
    AGENT_PHASE_PROCESSING_TOOL_RESULT_STARTED = "agent_phase_processing_tool_result_started"
    
    AGENT_PHASE_SHUTTING_DOWN_STARTED = "agent_phase_shutting_down_started"
    AGENT_PHASE_SHUTDOWN_COMPLETED = "agent_phase_shutdown_completed"
    AGENT_PHASE_ERROR_ENTERED = "agent_phase_error_entered"

    def __str__(self):
        return self.value

