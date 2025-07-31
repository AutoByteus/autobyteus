"""
Defines the main focus pane widget for displaying an agent's detailed log.
"""

import logging
import json
from typing import Optional, List

from rich.text import Text
from textual.message import Message
from textual.widgets import Input, Static
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
        self._current_stream_widget: Optional[Static] = None
        self._current_stream_text: Optional[Text] = None

    def compose(self):
        """Compose the widget's contents."""
        yield Static("No agent selected", id="focus-pane-title")
        yield VerticalScroll(id="focus-pane-log-container")
        yield Input(placeholder="Send a message to the focused agent...", id="focus-pane-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission."""
        text = event.value
        if text and self.focused_agent_name:
            log_container = self.query_one("#focus-pane-log-container")
            
            # --- NEW: Display the user's message immediately ---
            # Add a blank line for spacing before the user's message
            log_container.mount(Static(""))
            user_message_text = Text(f"You: {text}", style="bright_blue")
            log_container.mount(Static(user_message_text))
            log_container.scroll_end(animate=False)
            # --- END NEW ---

            logger.info(f"FocusPane: User submitted message for '{self.focused_agent_name}'.")
            self.post_message(self.MessageSubmitted(text, self.focused_agent_name))
            self.query_one(Input).clear()

    def set_agent_focus(self, agent_name: str, history: List[AgentStreamEvent]) -> None:
        """Sets the focus to a specific agent and populates it with history."""
        if self.focused_agent_name == agent_name:
            return

        logger.info(f"Switching focus pane to agent: '{agent_name}'.")
        self.focused_agent_name = agent_name
        self.query_one("#focus-pane-title").update(f"▼ [bold]{agent_name}[/bold]")
        
        self._clear_stream_state()
        
        log_container = self.query_one("#focus-pane-log-container")
        log_container.remove_children()

        # Replay the historical events to populate the pane
        for event in history:
            self.add_agent_event(event)
        
        self.query_one(Input).focus()

    def _clear_stream_state(self) -> None:
        """Resets the state of any ongoing text stream."""
        self._current_stream_widget = None
        self._current_stream_text = None

    def add_agent_event(self, event: AgentStreamEvent) -> None:
        """Adds a formatted log entry based on an agent event."""
        log_container = self.query_one("#focus-pane-log-container")

        # --- Streaming Logic for Assistant Chunks ---
        if event.event_type == AgentStreamEventType.ASSISTANT_CHUNK:
            data: AssistantChunkData = event.data
            
            if self._current_stream_widget is None:
                self._current_stream_text = Text()
                self._current_stream_widget = Static(self._current_stream_text)
                log_container.mount(self._current_stream_widget)

            if data.reasoning:
                self._current_stream_text.append(data.reasoning, style="dim italic cyan")
            if data.content:
                self._current_stream_text.append(data.content, style="default")

            self._current_stream_widget.update(self._current_stream_text)
            log_container.scroll_end(animate=False)
            return

        # --- Discrete Event Logic (for all other event types) ---
        self._clear_stream_state()
        
        formatted_text: Optional[Text] = None

        if event.event_type == AgentStreamEventType.ASSISTANT_COMPLETE_RESPONSE:
            data: AssistantCompleteResponseData = event.data
            if data.usage:
                usage_text = (
                    f"[Token Usage: Prompt={data.usage.prompt_tokens}, "
                    f"Completion={data.usage.completion_tokens}, Total={data.usage.total_tokens}]"
                )
                formatted_text = Text(usage_text, style="italic #8B8B8B")
            log_container.mount(Static(""))

        elif event.event_type == AgentStreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION:
            data: AgentOperationalPhaseTransitionData = event.data
            old_phase_str = data.old_phase.value if data.old_phase else 'None'
            msg = f"Phase: {old_phase_str} -> {data.new_phase.value}"
            if data.tool_name: msg += f" (tool: {data.tool_name})"
            if data.error_message: msg += f" (error: {data.error_message})"
            formatted_text = Text(msg, style="italic #8B8B8B")

        elif event.event_type == AgentStreamEventType.TOOL_INTERACTION_LOG_ENTRY:
            data: ToolInteractionLogEntryData = event.data
            formatted_text = Text(data.log_entry, style="#8B8B8B")

        elif event.event_type == AgentStreamEventType.TOOL_INVOCATION_AUTO_EXECUTING:
            data: ToolInvocationAutoExecutingData = event.data
            try:
                args_str = json.dumps(data.arguments, indent=2)
                msg = f"Auto-executing tool [bold]{data.tool_name}[/bold] with args:\n{args_str}"
            except Exception:
                args_str = str(data.arguments)
                msg = f"Auto-executing tool [bold]{data.tool_name}[/bold] with args: {args_str}"
            formatted_text = Text.from_markup(msg, style="yellow")

        elif event.event_type == AgentStreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED:
            data: ToolInvocationApprovalRequestedData = event.data
            try:
                args_str = json.dumps(data.arguments, indent=2)
                msg = f"Tool [bold]{data.tool_name}[/bold] is requesting approval with args:\n{args_str}\n(Approval not supported in TUI yet)"
            except Exception:
                args_str = str(data.arguments)
                msg = f"Tool [bold]{data.tool_name}[/bold] is requesting approval with args: {args_str}\n(Approval not supported in TUI yet)"
            formatted_text = Text.from_markup(msg, style="bold magenta")

        elif event.event_type == AgentStreamEventType.ERROR_EVENT:
            data: ErrorEventData = event.data
            msg = f"Error ({data.source}): {data.message}"
            formatted_text = Text(msg, style="bold red")
            if data.details:
                formatted_text.append("\n" + data.details, style="red")

        elif event.event_type == AgentStreamEventType.AGENT_IDLE:
            formatted_text = Text("Agent is now idle.", style="green")
        
        else:
            formatted_text = Text(f"Unhandled Event: {str(event)}", style="dim red")
        
        if formatted_text:
            log_container.mount(Static(formatted_text))
        
        log_container.scroll_end(animate=False)
