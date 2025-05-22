# file: autobyteus/autobyteus/agent/handlers/__init__.py
"""
Event handlers for agent runtime.
"""
from .base_event_handler import AgentEventHandler
from .event_handler_registry import EventHandlerRegistry
from .user_input_message_event_handler import UserInputMessageEventHandler 
from .inter_agent_message_event_handler import InterAgentMessageReceivedEventHandler 
from .llm_prompt_ready_event_handler import LLMPromptReadyEventHandler 
from .llm_complete_response_received_event_handler import LLMCompleteResponseReceivedEventHandler
from .tool_invocation_request_event_handler import ToolInvocationRequestEventHandler
from .tool_result_event_handler import ToolResultEventHandler
from .generic_event_handler import GenericEventHandler
from .lifecycle_event_logger import LifecycleEventLogger 
from .tool_execution_approval_event_handler import ToolExecutionApprovalEventHandler
from .approved_tool_invocation_event_handler import ApprovedToolInvocationEventHandler # Added new handler
# lifecycle_event_handler.py was in context, but not in __all__. If it's used, it should be exported.
# Assuming it was deprecated or replaced by LifecycleEventLogger based on previous context.
# If LifecycleEventHandler is still needed, it should be added here. For now, following existing exports.


__all__ = [
    "AgentEventHandler",
    "EventHandlerRegistry",
    "UserInputMessageEventHandler", 
    "InterAgentMessageReceivedEventHandler", 
    "LLMPromptReadyEventHandler",
    "LLMCompleteResponseReceivedEventHandler", 
    "ToolInvocationRequestEventHandler",
    "ToolResultEventHandler",
    "GenericEventHandler",
    "LifecycleEventLogger", 
    "ToolExecutionApprovalEventHandler",
    "ApprovedToolInvocationEventHandler", # Added new handler
]
