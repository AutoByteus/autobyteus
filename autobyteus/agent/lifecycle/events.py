# file: autobyteus/agent/lifecycle/events.py
"""
Defines the LifecycleEvent enum for user-facing lifecycle extension points.
These are simplified, intuitive event names that map internally to status transitions.
"""
from enum import Enum


class LifecycleEvent(str, Enum):
    """
    User-facing lifecycle events for agent extension.
    
    These events provide simple, intuitive hook points without requiring
    users to understand the internal status machine.
    """
    AGENT_READY = "agent_ready"
    """Triggered once after bootstrap completes and agent is ready for input."""
    
    BEFORE_LLM_CALL = "before_llm_call"
    """Triggered just before sending a request to the LLM."""
    
    AFTER_LLM_RESPONSE = "after_llm_response"
    """Triggered after receiving a complete LLM response."""
    
    BEFORE_TOOL_EXECUTE = "before_tool_execute"
    """Triggered just before a tool starts execution."""
    
    AFTER_TOOL_EXECUTE = "after_tool_execute"
    """Triggered after a tool completes execution."""
    
    AGENT_SHUTTING_DOWN = "agent_shutting_down"
    """Triggered when agent shutdown is initiated."""

    def __str__(self) -> str:
        return self.value
