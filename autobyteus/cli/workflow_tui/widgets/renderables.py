# file: autobyteus/autobyteus/cli/workflow_tui/widgets/renderables.py
"""
Contains pure functions that convert agent event data into Rich renderables for the FocusPane.
This separates presentation logic from the view logic of the widget itself.
"""
import json
from typing import Optional

from rich.text import Text
from rich.panel import Panel

from autobyteus.agent.streaming.stream_event_payloads import (
    AgentOperationalPhaseTransitionData, AssistantCompleteResponseData,
    ErrorEventData, ToolInteractionLogEntryData, ToolInvocationApprovalRequestedData, ToolInvocationAutoExecutingData
)
from .shared import ASSISTANT_ICON, TOOL_ICON, PROMPT_ICON, ERROR_ICON, LOG_ICON

def render_assistant_complete_response(data: AssistantCompleteResponseData) -> list[Text | Panel]:
    """Renders a complete, pre-aggregated assistant response."""
    renderables = []
    if data.reasoning:
        reasoning_text = Text("<Thinking>\n", style="dim italic cyan")
        reasoning_text.append(data.reasoning)
        reasoning_text.append("\n</Thinking>", style="dim italic cyan")
        renderables.append(reasoning_text)
    
    if data.content:
        content_text = Text()
        content_text.append(f"{ASSISTANT_ICON} assistant: ", style="bold green")
        content_text.append(data.content)
        renderables.append(content_text)
    
    return renderables

def render_tool_interaction_log(data: ToolInteractionLogEntryData) -> Text:
    """Renders a tool interaction log entry."""
    return Text(f"{LOG_ICON} [tool-log] {data.log_entry}", style="dim")

def render_tool_auto_executing(data: ToolInvocationAutoExecutingData) -> Text:
    """Renders a notification that a tool is being executed automatically."""
    try:
        args_str = json.dumps(data.arguments, indent=2)
    except (TypeError, OverflowError):
        args_str = str(data.arguments)
        
    text_content = Text(f"{TOOL_ICON} Executing tool '", style="default")
    text_content.append(f"{data.tool_name}", style="bold yellow")
    text_content.append("' with arguments:\n", style="default")
    text_content.append(args_str, style="yellow")
    return text_content
    
def render_tool_approval_request(data: ToolInvocationApprovalRequestedData) -> Text:
    """Renders a prompt for the user to approve a tool call."""
    try:
        args_str = json.dumps(data.arguments, indent=2)
    except (TypeError, OverflowError):
        args_str = str(data.arguments)

    text_content = Text(f"{PROMPT_ICON} Requesting approval for tool '", style="default")
    text_content.append(f"{data.tool_name}", style="bold yellow")
    text_content.append("' with arguments:\n", style="default")
    text_content.append(args_str, style="yellow")
    return text_content

def render_error(data: ErrorEventData) -> Text:
    """Renders an error event."""
    error_text = f"Error from {data.source}: {data.message}"
    if data.details: 
        error_text += f"\nDetails: {data.details}"
    return Text(f"{ERROR_ICON} {error_text}", style="bold red")
