# file: autobyteus/autobyteus/agent/context/phases.py
from enum import Enum

class AgentOperationalPhase(str, Enum):
    """
    Defines the fine-grained operational phases of an agent.
    This is the single source of truth for an agent's current state of operation.
    """
    UNINITIALIZED = "uninitialized"            # Agent object created, but runtime not started or fully set up.
    BOOTSTRAPPING = "bootstrapping"            # Agent is running its internal initialization/bootstrap sequence.
    IDLE = "idle"                              # Fully initialized and ready for new input.
    
    PROCESSING_USER_INPUT = "processing_user_input"     # Actively processing a user message, typically preparing for an LLM call.
    AWAITING_LLM_RESPONSE = "awaiting_llm_response"     # Sent a request to LLM, waiting for the full response or stream.
    ANALYZING_LLM_RESPONSE = "analyzing_llm_response"   # Received LLM response, analyzing it for next actions (e.g., tool use, direct reply).
    
    AWAITING_TOOL_APPROVAL = "awaiting_tool_approval"   # Paused, needs external (user) approval for a tool invocation.
    TOOL_DENIED = "tool_denied"                         # A proposed tool execution was denied by the user. Agent is processing the denial.
    EXECUTING_TOOL = "executing_tool"                   # Tool has been approved (or auto-approved) and is currently running.
    PROCESSING_TOOL_RESULT = "processing_tool_result"   # Received a tool's result, actively processing it (often leading to another LLM call).
    
    SHUTTING_DOWN = "shutting_down"               # Shutdown sequence has been initiated.
    SHUTDOWN_COMPLETE = "shutdown_complete"       # Agent has fully stopped and released resources.
    ERROR = "error"                               # An unrecoverable error has occurred. Agent might be non-operational.

    def __str__(self) -> str:
        return self.value

    def is_initializing(self) -> bool:
        """Checks if the agent is in any of the initializing phases."""
        return self in [
            AgentOperationalPhase.BOOTSTRAPPING,
        ]

    def is_processing(self) -> bool:
        """Checks if the agent is in any active processing phase (post-initialization, pre-shutdown)."""
        return self in [
            AgentOperationalPhase.PROCESSING_USER_INPUT,
            AgentOperationalPhase.AWAITING_LLM_RESPONSE,
            AgentOperationalPhase.ANALYZING_LLM_RESPONSE,
            AgentOperationalPhase.AWAITING_TOOL_APPROVAL,
            AgentOperationalPhase.TOOL_DENIED,
            AgentOperationalPhase.EXECUTING_TOOL,
            AgentOperationalPhase.PROCESSING_TOOL_RESULT,
        ]
    
    def is_terminal(self) -> bool:
        """Checks if the phase is a terminal state (shutdown or error)."""
        return self in [AgentOperationalPhase.SHUTDOWN_COMPLETE, AgentOperationalPhase.ERROR]
