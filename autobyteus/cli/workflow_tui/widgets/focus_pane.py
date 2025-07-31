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
from .shared import AGENT_PHASE_ICONS, WORKFLOW_PHASE_ICONS, SUB_WORKFLOW_ICON, DEFAULT_ICON

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
        self._focused_node_name: Optional[str] = None
        self._focused_node_type: Optional[str] = None
        self._pending_approval_data: Optional[ToolInvocationApprovalRequestedData] = None
        self._current_stream_widget: Optional[Static] = None
        self._current_stream_text: Optional[Text] = None

    def compose(self):
        yield Static("Select a node from the sidebar", id="focus-pane-title")
        yield VerticalScroll(id="focus-pane-log-container")
        yield Horizontal(id="approval-buttons")
        yield Input(placeholder="Select an agent to send messages...", id="focus-pane-input", disabled=True)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value and self._focused_node_name and self._focused_node_type == 'agent':
            log_container = self.query_one("#focus-pane-log-container")
            user_message_text = Text(f"You: {event.value}", style="bright_blue")
            await log_container.mount(Static(""))
            await log_container.mount(Static(user_message_text))
            log_container.scroll_end(animate=False)
            
            self.post_message(self.MessageSubmitted(event.value, self._focused_node_name))
            self.query_one(Input).clear()
        event.stop()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self._pending_approval_data or not self._focused_node_name:
            return

        is_approved = event.button.id == "approve-btn"
        reason = "User approved via TUI." if is_approved else "User denied via TUI."
        
        log_container = self.query_one("#focus-pane-log-container")
        approval_text = "APPROVED" if is_approved else "DENIED"
        display_text = Text(f"You: {approval_text} (Reason: {reason})", style="bright_cyan")
        await log_container.mount(Static(""))
        await log_container.mount(Static(display_text))
        log_container.scroll_end(animate=False)

        self.post_message(self.ApprovalSubmitted(
            agent_name=self._focused_node_name,
            invocation_id=self._pending_approval_data.invocation_id,
            is_approved=is_approved, reason=reason
        ))
        await self._clear_approval_ui()
        event.stop()

    async def _clear_approval_ui(self):
        self._pending_approval_data = None
        await self.query_one("#approval-buttons").remove_children()
        input_widget = self.query_one(Input)
        if self._focused_node_type == "agent":
            input_widget.disabled = False
            input_widget.placeholder = f"Send a message to {self._focused_node_name}..."
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

    async def update_content(self, node_data: Dict[str, Any], history: List[Any], 
                             pending_approval: Optional[ToolInvocationApprovalRequestedData], 
                             all_agent_phases: Dict[str, AgentOperationalPhase], 
                             all_workflow_phases: Dict[str, WorkflowOperationalPhase]):
        """The main method to update the entire pane based on new state.
        This is called when focus SWITCHES."""
        self._focused_node_name = node_data['name']
        self._focused_node_type = node_data['type']
        self._pending_approval_data = pending_approval
        
        node_name = node_data.get("name", "Unknown")
        node_type_str = node_data.get("type", "node").replace("_", " ").capitalize()
        
        self.query_one("#focus-pane-title").update(f"▼ {node_type_str}: [bold]{node_name}[/bold]")

        log_container = self.query_one("#focus-pane-log-container")
        await log_container.remove_children()
        self._current_stream_widget = None
        self._current_stream_text = None
        await self._clear_approval_ui()

        if self._focused_node_type == 'agent':
            for event in history:
                await self.add_agent_event(event)
            if self._pending_approval_data:
                await self._show_approval_prompt()
        elif self._focused_node_type in ['workflow', 'subworkflow']:
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

    async def add_agent_event(self, event: AgentStreamEvent):
        """Adds a single agent event to the log view, enabling live streaming."""
        log_container = self.query_one("#focus-pane-log-container")
        widget_to_mount: Optional[Static] = None

        if event.event_type == AgentStreamEventType.ASSISTANT_CHUNK:
            data: AssistantChunkData = event.data
            # If this is the start of a new stream of text
            if self._current_stream_widget is None:
                await log_container.mount(Static("")) # Add spacing
                self._current_stream_text = Text()
                self._current_stream_widget = Static(self._current_stream_text)
                await log_container.mount(self._current_stream_widget)

            # Prepend "assistant: " to the very first chunk of a stream
            if not self._current_stream_text:
                self._current_stream_text.append("assistant: ", style="bold green")
            
            # Append reasoning and content
            if data.reasoning: self._current_stream_text.append(data.reasoning, style="dim italic cyan")
            if data.content: self._current_stream_text.append(data.content, style="default")
            
            self._current_stream_widget.update(self._current_stream_text)
            log_container.scroll_end(animate=False)
            return

        # Any other event breaks the stream.
        self._current_stream_widget = None
        self._current_stream_text = None
        
        # Add spacing before rendering a new, non-chunk event
        await log_container.mount(Static(""))
        
        if event.event_type == AgentStreamEventType.ASSISTANT_COMPLETE_RESPONSE:
            pass # Avoid duplicate content
        
        elif event.event_type == AgentStreamEventType.TOOL_INTERACTION_LOG_ENTRY:
            data: ToolInteractionLogEntryData = event.data
            log_text = Text(f"[tool-log] {data.log_entry}", style="dim")
            widget_to_mount = Static(log_text)

        elif event.event_type == AgentStreamEventType.TOOL_INVOCATION_AUTO_EXECUTING:
            data: ToolInvocationAutoExecutingData = event.data
            args_str = json.dumps(data.arguments, indent=2)
            text_content = Text()
            text_content.append("Executing tool '", style="default")
            text_content.append(f"{data.tool_name}", style="bold yellow")
            text_content.append("' with arguments:\n", style="default")
            text_content.append(args_str, style="yellow")
            widget_to_mount = Static(text_content)

        elif event.event_type == AgentStreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED:
            data: ToolInvocationApprovalRequestedData = event.data
            args_str = json.dumps(data.arguments, indent=2)
            text_content = Text()
            text_content.append("Requesting approval for tool '", style="default")
            text_content.append(f"{data.tool_name}", style="bold yellow")
            text_content.append("' with arguments:\n", style="default")
            text_content.append(args_str, style="yellow")
            widget_to_mount = Static(text_content)
            self._pending_approval_data = data
            await self._show_approval_prompt()
        
        elif event.event_type == AgentStreamEventType.ERROR_EVENT:
            data: ErrorEventData = event.data
            error_text = f"Error from {data.source}: {data.message}"
            if data.details: error_text += f"\nDetails: {data.details}"
            widget_to_mount = Static(Text(error_text, style="bold red"))
            
        elif event.event_type == AgentStreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION:
            data: AgentOperationalPhaseTransitionData = event.data
            old_phase = data.old_phase.value if data.old_phase else 'uninitialized'
            phase_text = Text(f"Phase: {old_phase} -> {data.new_phase.value}", style="italic dim")
            widget_to_mount = Static(phase_text)

        if widget_to_mount:
            await log_container.mount(widget_to_mount)
        
        log_container.scroll_end(animate=False)
