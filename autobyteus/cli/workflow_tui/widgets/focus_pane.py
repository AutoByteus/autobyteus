# file: autobyteus/autobyteus/cli/workflow_tui/widgets/focus_pane.py
"""
Defines the main focus pane widget for displaying detailed logs or summaries.
"""
import logging
import json
from typing import Optional, List, Any, Dict

from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from textual.message import Message
from textual.widgets import Input, Static, Button
from textual.containers import VerticalScroll, Horizontal

from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.workflow.phases import WorkflowOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent, StreamEventType as AgentStreamEventType
from autobyteus.agent.streaming.stream_event_payloads import (
    AgentOperationalPhaseTransitionData, AssistantChunkData, AssistantCompleteResponseData,
    ErrorEventData, ToolInteractionLogEntryData, ToolInvocationApprovalRequestedData, ToolInvocationAutoExecutingData
)
from .shared import (
    AGENT_PHASE_ICONS, WORKFLOW_PHASE_ICONS, SUB_WORKFLOW_ICON, DEFAULT_ICON,
    USER_ICON, ASSISTANT_ICON, WORKFLOW_ICON, AGENT_ICON
)
from . import renderables

logger = logging.getLogger(__name__)

class FocusPane(Static):
    """
    A widget to display detailed logs for agents or high-level dashboards for workflows.
    This is a dumb rendering component driven by the TUIStateStore.
    """

    class MessageSubmitted(Message):
        def __init__(self, text: str, agent_name: str) -> None:
            self.text = text
            self.agent_name = agent_name
            super().__init__()

    class ApprovalSubmitted(Message):
        def __init__(self, agent_name: str, invocation_id: str, is_approved: bool, reason: Optional[str]) -> None:
            self.agent_name = agent_name
            self.invocation_id = invocation_id
            self.is_approved = is_approved
            self.reason = reason
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._focused_node_data: Optional[Dict[str, Any]] = None
        self._pending_approval_data: Optional[ToolInvocationApprovalRequestedData] = None
        
        # State variables for streaming
        self._thinking_widget: Optional[Static] = None
        self._thinking_text: Optional[Text] = None
        self._assistant_content_widget: Optional[Static] = None
        self._assistant_content_text: Optional[Text] = None
        
        # Buffers for batched UI updates to improve performance
        self._reasoning_buffer: str = ""
        self._content_buffer: str = ""

    def compose(self):
        yield Static("Select a node from the sidebar", id="focus-pane-title")
        yield VerticalScroll(id="focus-pane-log-container")
        yield Horizontal(id="approval-buttons")
        yield Input(placeholder="Select an agent to send messages...", id="focus-pane-input", disabled=True)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value and self._focused_node_data and self._focused_node_data.get("type") == 'agent':
            log_container = self.query_one("#focus-pane-log-container")
            user_message_text = Text(f"{USER_ICON} You: {event.value}", style="bright_blue")
            await log_container.mount(Static(""))
            await log_container.mount(Static(user_message_text))
            log_container.scroll_end(animate=False)
            
            self.post_message(self.MessageSubmitted(event.value, self._focused_node_data['name']))
            self.query_one(Input).clear()
        event.stop()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self._pending_approval_data or not self._focused_node_data:
            return

        is_approved = event.button.id == "approve-btn"
        reason = "User approved via TUI." if is_approved else "User denied via TUI."
        
        log_container = self.query_one("#focus-pane-log-container")
        approval_text = "APPROVED" if is_approved else "DENIED"
        display_text = Text(f"{USER_ICON} You: {approval_text} (Reason: {reason})", style="bright_cyan")
        await log_container.mount(Static(""))
        await log_container.mount(Static(display_text))
        log_container.scroll_end(animate=False)

        self.post_message(self.ApprovalSubmitted(
            agent_name=self._focused_node_data['name'],
            invocation_id=self._pending_approval_data.invocation_id,
            is_approved=is_approved, reason=reason
        ))
        await self._clear_approval_ui()
        event.stop()

    async def _clear_approval_ui(self):
        self._pending_approval_data = None
        await self.query_one("#approval-buttons").remove_children()
        input_widget = self.query_one(Input)
        if self._focused_node_data and self._focused_node_data.get("type") == "agent":
            input_widget.disabled = False
            input_widget.placeholder = f"Send a message to {self._focused_node_data['name']}..."
            input_widget.focus()
        else:
            input_widget.disabled = True
            input_widget.placeholder = "Select an agent to send messages..."

    async def _show_approval_prompt(self):
        if not self._pending_approval_data: return
        input_widget = self.query_one(Input)
        input_widget.placeholder = "Please approve or deny the tool call..."
        input_widget.disabled = True
        button_container = self.query_one("#approval-buttons")
        await button_container.remove_children()
        await button_container.mount(
            Button("Approve", variant="success", id="approve-btn"),
            Button("Deny", variant="error", id="deny-btn")
        )

    def _update_title(self, agent_phases: Dict[str, AgentOperationalPhase], workflow_phases: Dict[str, WorkflowOperationalPhase]):
        """Renders the title of the focus pane with the node's current status."""
        if not self._focused_node_data:
            self.query_one("#focus-pane-title").update("Select a node from the sidebar")
            return

        node_name = self._focused_node_data.get("name", "Unknown")
        node_type = self._focused_node_data.get("type", "node")
        node_type_str = node_type.replace("_", " ").capitalize()

        title_icon = DEFAULT_ICON
        phase_str = ""

        if node_type == 'agent':
            title_icon = AGENT_ICON
            phase = agent_phases.get(node_name, AgentOperationalPhase.UNINITIALIZED)
            phase_str = f" (Status: {phase.value})"
        elif node_type == 'subworkflow':
            title_icon = SUB_WORKFLOW_ICON
            phase = workflow_phases.get(node_name, WorkflowOperationalPhase.UNINITIALIZED)
            phase_str = f" (Status: {phase.value})"
        elif node_type == 'workflow':
            title_icon = WORKFLOW_ICON
            phase = workflow_phases.get(node_name, WorkflowOperationalPhase.UNINITIALIZED)
            phase_str = f" (Status: {phase.value})"

        self.query_one("#focus-pane-title").update(f"{title_icon} {node_type_str}: [bold]{node_name}[/bold]{phase_str}")
        
    def update_current_node_status(self, all_agent_phases: Dict, all_workflow_phases: Dict):
        """A lightweight method to only update the title with the latest status."""
        self._update_title(all_agent_phases, all_workflow_phases)

    async def update_content(self, node_data: Dict[str, Any], history: List[Any], 
                             pending_approval: Optional[ToolInvocationApprovalRequestedData], 
                             all_agent_phases: Dict[str, AgentOperationalPhase], 
                             all_workflow_phases: Dict[str, WorkflowOperationalPhase]):
        """The main method to update the entire pane based on new state.
        This is called when focus SWITCHES, or when data for a focused workflow is REFRESHED."""
        self.flush_stream_buffers()

        self._focused_node_data = node_data
        self._pending_approval_data = pending_approval
        
        self._update_title(all_agent_phases, all_workflow_phases)

        log_container = self.query_one("#focus-pane-log-container")
        await log_container.remove_children()

        # Reset streaming state
        self._thinking_widget = None
        self._thinking_text = None
        self._assistant_content_widget = None
        self._assistant_content_text = None

        await self._clear_approval_ui()

        if self._focused_node_data.get("type") == 'agent':
            for event in history:
                await self.add_agent_event(event)
            if self._pending_approval_data:
                await self._show_approval_prompt()
        elif self._focused_node_data.get("type") in ['workflow', 'subworkflow']:
            await self._render_workflow_dashboard(node_data, all_agent_phases, all_workflow_phases)

    async def _render_workflow_dashboard(self, node_data: Dict[str, Any], 
                                         all_agent_phases: Dict[str, AgentOperationalPhase],
                                         all_workflow_phases: Dict[str, WorkflowOperationalPhase]):
        """Renders a static summary dashboard for a workflow or sub-workflow."""
        log_container = self.query_one("#focus-pane-log-container")
        
        phase = all_workflow_phases.get(node_data['name'], WorkflowOperationalPhase.UNINITIALIZED)
        phase_icon = WORKFLOW_PHASE_ICONS.get(phase, DEFAULT_ICON)
        info_text = Text()
        info_text.append(f"Name: {node_data['name']}\n", style="bold")
        if node_data.get('role'):
            info_text.append(f"Role: {node_data['role']}\n")
        info_text.append(f"Status: {phase_icon} {phase.value}")
        await log_container.mount(Static(Panel(info_text, title="Workflow Info", border_style="green", title_align="left")))

        children_data = node_data.get("children", {})
        if children_data:
            team_text = Text()
            for name, child_node in children_data.items():
                if child_node['type'] == 'agent':
                    agent_phase = all_agent_phases.get(name, AgentOperationalPhase.UNINITIALIZED)
                    agent_icon = AGENT_PHASE_ICONS.get(agent_phase, DEFAULT_ICON)
                    team_text.append(f" ▪ {agent_icon} {name} (Agent): {agent_phase.value}\n")
                elif child_node['type'] == 'subworkflow':
                    wf_phase = all_workflow_phases.get(name, WorkflowOperationalPhase.UNINITIALIZED)
                    wf_icon = WORKFLOW_PHASE_ICONS.get(wf_phase, SUB_WORKFLOW_ICON)
                    team_text.append(f" ▪ {wf_icon} {name} (Sub-Workflow): {wf_phase.value}\n")
            await log_container.mount(Static(Panel(team_text, title="Team Status", border_style="blue", title_align="left")))

    async def _close_thinking_block(self, scroll: bool = True):
        """Finalizes and closes the current thinking block if it's open."""
        if self._thinking_widget and self._thinking_text:
            self.flush_stream_buffers() # Ensure any buffered reasoning is flushed first
            self._thinking_text.append("\n</Thinking>", style="dim italic cyan")
            self._thinking_widget.update(self._thinking_text)
            if scroll:
                self.query_one("#focus-pane-log-container").scroll_end(animate=False)
            self._thinking_widget = None
            self._thinking_text = None

    def flush_stream_buffers(self):
        """Flushes the content of the stream buffers to the UI."""
        scrolled = False
        if self._reasoning_buffer and self._thinking_widget and self._thinking_text:
            self._thinking_text.append(self._reasoning_buffer)
            self._thinking_widget.update(self._thinking_text)
            self._reasoning_buffer = ""
            scrolled = True

        if self._content_buffer and self._assistant_content_widget and self._assistant_content_text:
            self._assistant_content_text.append(self._content_buffer)
            self._assistant_content_widget.update(self._assistant_content_text)
            self._content_buffer = ""
            scrolled = True
        
        if scrolled:
            self.query_one("#focus-pane-log-container").scroll_end(animate=False)

    async def add_agent_event(self, event: AgentStreamEvent):
        """Adds a single agent event to the log view, handling stream state correctly."""
        log_container = self.query_one("#focus-pane-log-container")
        event_type = event.event_type

        # Handle streaming content events
        if event_type == AgentStreamEventType.ASSISTANT_CHUNK:
            data: AssistantChunkData = event.data
            if data.reasoning:
                if self._thinking_widget is None:
                    self.flush_stream_buffers()
                    await log_container.mount(Static(""))
                    self._thinking_text = Text("<Thinking>\n", style="dim italic cyan")
                    self._thinking_widget = Static(self._thinking_text)
                    await log_container.mount(self._thinking_widget)
                self._reasoning_buffer += data.reasoning

            if data.content:
                if self._thinking_widget:
                    await self._close_thinking_block()
                if self._assistant_content_widget is None:
                    await log_container.mount(Static(""))
                    self._assistant_content_text = Text()
                    self._assistant_content_text.append(f"{ASSISTANT_ICON} assistant: ", style="bold green")
                    self._assistant_content_widget = Static(self._assistant_content_text)
                    await log_container.mount(self._assistant_content_widget)
                self._content_buffer += data.content
            return  # This event is handled, do nothing more.

        # Handle the explicit end of a stream
        if event_type == AgentStreamEventType.ASSISTANT_COMPLETE_RESPONSE:
            was_streaming_content = self._assistant_content_widget is not None
            self.flush_stream_buffers()
            await self._close_thinking_block()
            self._assistant_content_widget = None
            self._assistant_content_text = None

            # If we weren't streaming, it means this is a non-streamed response. We should render it.
            if not was_streaming_content:
                renderables_list = renderables.render_assistant_complete_response(event.data)
                if renderables_list:
                    await log_container.mount(Static(""))
                    for item in renderables_list:
                        await log_container.mount(Static(item))
                    log_container.scroll_end(animate=False)
            return  # This event's purpose is to end the stream.

        # For all other events, first check if they should break an ongoing stream.
        is_stream_breaking_event = event_type in [
            AgentStreamEventType.TOOL_INTERACTION_LOG_ENTRY,
            AgentStreamEventType.TOOL_INVOCATION_AUTO_EXECUTING,
            AgentStreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED,
            AgentStreamEventType.ERROR_EVENT,
        ]

        if is_stream_breaking_event:
            # Finalize any open assistant block before rendering this event.
            self.flush_stream_buffers()
            await self._close_thinking_block()
            self._assistant_content_widget = None
            self._assistant_content_text = None
        
        # Now, render the event if it has a visual representation.
        renderable = None
        
        if event_type == AgentStreamEventType.TOOL_INTERACTION_LOG_ENTRY:
            renderable = renderables.render_tool_interaction_log(event.data)
        elif event_type == AgentStreamEventType.TOOL_INVOCATION_AUTO_EXECUTING:
            renderable = renderables.render_tool_auto_executing(event.data)
        elif event_type == AgentStreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED:
            renderable = renderables.render_tool_approval_request(event.data)
            self._pending_approval_data = event.data
            await self._show_approval_prompt()
        elif event_type == AgentStreamEventType.ERROR_EVENT:
            renderable = renderables.render_error(event.data)
        elif event_type in [AgentStreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION, AgentStreamEventType.AGENT_IDLE]:
            # These are informational and do not have a renderable in the log pane.
            pass

        if renderable:
            await log_container.mount(Static("")) # Add spacer
            await log_container.mount(Static(renderable))

        log_container.scroll_end(animate=False)
