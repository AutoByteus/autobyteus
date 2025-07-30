# file: autobyteus/autobyteus/cli/workflow_tui/widgets/focus_pane.py
"""
Defines the main focus pane widget for displaying an agent's detailed log.
"""

import logging
import json
from typing import Optional

from rich.text import Text
from textual.message import Message
from textual.widgets import Input, RichLog, Static
from textual.containers import VerticalScroll

from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent, StreamEventType as AgentStreamEventType
from autobyteus.agent.streaming.stream_event_payloads import (
    AgentOperationalPhaseTransitionData,
    AssistantChunkData,
    AssistantCompleteResponseData,
    ErrorEventData,
    ToolInteractionLogEntryData,
    ToolInvocationApprovalRequestedData,
    ToolInvocationAutoExecutingData,
)

logger = logging.getLogger(__name__)

class FocusPane(Static):
    """A widget to display the detailed log and input for a single agent."""

    class MessageSubmitted(Message):
        """Posted when a message is submitted from the input."""
        def __init__(self, text: str, agent_name: str) -> None:
            self.text = text
            self.agent_name = agent_name
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.focused_agent_name: str = ""
        self._current_stream_style: Optional[str] = None

    def compose(self):
        """Compose the widget's contents."""
        yield Static("No agent selected", id="focus-pane-title")
        with VerticalScroll(id="focus-pane-log-container"):
            yield RichLog(id="focus-pane-log", wrap=True, highlight=True, markup=True)
        yield Input(placeholder="Send a message to the focused agent...", id="focus-pane-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission."""
        text = event.value
        if text and self.focused_agent_name:
            logger.info(f"FocusPane: User submitted message for '{self.focused_agent_name}'.")
            self.post_message(self.MessageSubmitted(text, self.focused_agent_name))
            self.query_one(Input).clear()

    def set_agent_focus(self, agent_name: str) -> None:
        """Sets the focus to a specific agent."""
        if self.focused_agent_name == agent_name:
            return # No change needed

        logger.info(f"Switching focus pane to agent: '{agent_name}'.")
        self.focused_agent_name = agent_name
        self._clear_stream_state()
        self.query_one("#focus-pane-title").update(f"▼ [bold]{agent_name}[/bold]")
        self.query_one(RichLog).clear()
        self.query_one(Input).focus()

    def _clear_stream_state(self) -> None:
        """Resets the state of any ongoing text stream."""
        self._current_stream_style = None

    def add_agent_event(self, event: AgentStreamEvent) -> None:
        """Adds a formatted log entry based on an agent event."""
        log = self.query_one(RichLog)

        # --- Streaming Logic for Assistant Chunks ---
        if event.event_type == AgentStreamEventType.ASSISTANT_CHUNK:
            data: AssistantChunkData = event.data

            def stream_append(text: str, style: str):
                """Appends text to the log, either on a new line or the last line."""
                if not text:
                    return

                # Determine if we can append to the last line.
                can_append = (
                    log.lines and
                    self._current_stream_style == style and
                    isinstance(log.lines[-1], Text)  # This is the crucial fix.
                )
                
                if can_append:
                    # Append to the last existing line, which is confirmed to be a Text object.
                    log.lines[-1].append(text, style=style)
                    # When manipulating lines directly, we must invalidate the cache and refresh.
                    if hasattr(log, "_line_cache"):
                        log._line_cache.clear()
                    log.refresh()
                else:
                    # Start a new line if the log is empty, the style has changed,
                    # or the last line is not appendable.
                    self._current_stream_style = style
                    log.write(Text(text, style=style))
            
            # Stream reasoning and content if they exist
            stream_append(data.reasoning or "", "dim italic cyan")
            stream_append(data.content or "", "default")
            return

        # --- Discrete Event Logic (for all other event types) ---
        self._clear_stream_state()

        if event.event_type == AgentStreamEventType.ASSISTANT_COMPLETE_RESPONSE:
            data: AssistantCompleteResponseData = event.data
            if data.usage:
                usage_text = (
                    f"[Token Usage: Prompt={data.usage.prompt_tokens}, "
                    f"Completion={data.usage.completion_tokens}, Total={data.usage.total_tokens}]"
                )
                log.write(Text(usage_text, style="dim"))
            log.write("")  # Add a blank line for separation

        elif event.event_type == AgentStreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION:
            data: AgentOperationalPhaseTransitionData = event.data
            old_phase_str = data.old_phase.value if data.old_phase else 'None'
            msg = f"Phase: {old_phase_str} -> {data.new_phase.value}"
            if data.tool_name:
                msg += f" (tool: {data.tool_name})"
            if data.error_message:
                msg += f" (error: {data.error_message})"
            log.write(Text(msg, style="dim"))

        elif event.event_type == AgentStreamEventType.TOOL_INTERACTION_LOG_ENTRY:
            data: ToolInteractionLogEntryData = event.data
            log.write(Text(data.log_entry, style="bright_black"))

        elif event.event_type == AgentStreamEventType.TOOL_INVOCATION_AUTO_EXECUTING:
            data: ToolInvocationAutoExecutingData = event.data
            try:
                args_str = json.dumps(data.arguments, indent=2)
                msg = f"Auto-executing tool [bold]{data.tool_name}[/bold] with args:\n{args_str}"
            except Exception:
                args_str = str(data.arguments)
                msg = f"Auto-executing tool [bold]{data.tool_name}[/bold] with args: {args_str}"
            log.write(Text.from_markup(msg, style="yellow"))

        elif event.event_type == AgentStreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED:
            data: ToolInvocationApprovalRequestedData = event.data
            try:
                args_str = json.dumps(data.arguments, indent=2)
                msg = f"Tool [bold]{data.tool_name}[/bold] is requesting approval with args:\n{args_str}\n(Approval not supported in TUI yet)"
            except Exception:
                args_str = str(data.arguments)
                msg = f"Tool [bold]{data.tool_name}[/bold] is requesting approval with args: {args_str}\n(Approval not supported in TUI yet)"
            log.write(Text.from_markup(msg, style="bold magenta"))

        elif event.event_type == AgentStreamEventType.ERROR_EVENT:
            data: ErrorEventData = event.data
            msg = f"Error ({data.source}): {data.message}"
            log.write(Text(msg, style="bold red"))
            if data.details:
                log.write(Text(data.details, style="red"))

        elif event.event_type == AgentStreamEventType.AGENT_IDLE:
            log.write(Text("Agent is now idle.", style="dim green"))
            
        else:
            log.write(Text(f"Unhandled Event: {str(event)}", style="dim red"))
