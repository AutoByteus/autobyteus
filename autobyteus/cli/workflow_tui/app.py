# file: autobyteus/autobyteus/cli/workflow_tui/app.py
"""
The main Textual application class for the workflow TUI.
"""

import asyncio
import logging
from typing import Dict, Optional, List

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Tree

from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.workflow.streaming.workflow_event_stream import WorkflowEventStream
from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent, StreamEventType as AgentStreamEventType
from autobyteus.agent.streaming.stream_event_payloads import AgentOperationalPhaseTransitionData, AssistantChunkData
from autobyteus.workflow.streaming.workflow_stream_event_payloads import AgentEventRebroadcastPayload

from .widgets.agent_list_sidebar import AgentListSidebar
from .widgets.focus_pane import FocusPane
from .widgets.status_bar import StatusBar

logger = logging.getLogger(__name__)

class WorkflowApp(App):
    """A Textual TUI for interacting with an agentic workflow."""

    TITLE = "AutoByteus"

    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Force Quit"),
    ]

    def __init__(self, workflow: AgenticWorkflow, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(workflow, AgenticWorkflow):
            raise TypeError("WorkflowApp requires an AgenticWorkflow instance.")
        self.workflow = workflow
        self.workflow_stream: Optional[WorkflowEventStream] = None
        self.agent_phases: Dict[str, AgentOperationalPhase] = {}
        self.agent_event_history: Dict[str, List[AgentStreamEvent]] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(id="app-header", name="AutoByteus")
        with Horizontal(id="main-container"):
            yield AgentListSidebar(id="sidebar")
            yield FocusPane(id="focus-pane")
        yield StatusBar()

    async def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.workflow.start()
        self.workflow_stream = WorkflowEventStream(self.workflow)
        self.run_worker(self._listen_for_workflow_events(), name="workflow_listener", group="listeners")
        logger.info("Workflow TUI mounted and workflow listener started.")

    async def on_unmount(self) -> None:
        """Called when the app is unmounted, before exiting."""
        logger.info("TUI is unmounting. Stopping the workflow...")
        if self.workflow and self.workflow.is_running:
            await self.workflow.stop()
        logger.info("Workflow stop command issued from TUI.")

    async def _listen_for_workflow_events(self) -> None:
        """A background worker that listens for and processes workflow events."""
        if not self.workflow_stream:
            return

        sidebar = self.query_one(AgentListSidebar)
        focus_pane = self.query_one(FocusPane)
        
        try:
            async for event in self.workflow_stream.all_events():
                if event.event_source_type != "AGENT" or not isinstance(event.data, AgentEventRebroadcastPayload):
                    continue

                payload: AgentEventRebroadcastPayload = event.data
                agent_name = payload.agent_name
                agent_event = payload.agent_event

                if agent_name not in self.agent_event_history:
                    self.agent_event_history[agent_name] = []
                self.agent_event_history[agent_name].append(agent_event)

                if agent_name not in sidebar._agent_nodes:
                    is_coordinator = agent_name.lower().startswith("coordinator") or "manager" in agent_name.lower()
                    sidebar.add_agent(agent_name, is_coordinator=is_coordinator)
                    if is_coordinator:
                        history = self.agent_event_history.get(agent_name, [])
                        focus_pane.set_agent_focus(agent_name, history)

                # --- Auto-focus switching logic ---
                if agent_event.event_type == AgentStreamEventType.ASSISTANT_CHUNK:
                    chunk_data: AssistantChunkData = agent_event.data
                    if chunk_data.content and agent_name != focus_pane.focused_agent_name:
                        logger.info(f"Auto-switching focus to '{agent_name}' due to ASSISTANT_CHUNK event.")
                        history = self.agent_event_history.get(agent_name, [])
                        focus_pane.set_agent_focus(agent_name, history)
                        
                        if agent_name in sidebar._agent_nodes:
                            tree = sidebar.query_one(Tree)
                            node_to_select = sidebar._agent_nodes[agent_name]
                            tree.select_node(node_to_select)
                            # FIX: Removed the unsupported 'top' keyword argument.
                            tree.scroll_to_node(node_to_select, animate=True)

                if agent_event.event_type == AgentStreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION:
                    phase_data: AgentOperationalPhaseTransitionData = agent_event.data
                    self.agent_phases[agent_name] = phase_data.new_phase
                    sidebar.update_agent_status(agent_name, phase_data.new_phase)
                
                if agent_event.event_type == AgentStreamEventType.ASSISTANT_CHUNK:
                    chunk_data: AssistantChunkData = agent_event.data
                    if chunk_data.content:
                        base_phase = self.agent_phases.get(agent_name, AgentOperationalPhase.IDLE)
                        sidebar.update_agent_activity_to_speaking(agent_name, base_phase)

                if agent_name == focus_pane.focused_agent_name:
                    focus_pane.add_agent_event(agent_event)

        except asyncio.CancelledError:
            logger.info("Workflow event listener task was cancelled.")
        except Exception:
            logger.error("An error occurred in the workflow event listener", exc_info=True)
        finally:
            if self.workflow_stream:
                await self.workflow_stream.close()

    async def on_agent_list_sidebar_agent_selected(self, message: AgentListSidebar.AgentSelected) -> None:
        """Handle an agent being selected in the sidebar."""
        history = self.agent_event_history.get(message.agent_name, [])
        self.query_one(FocusPane).set_agent_focus(message.agent_name, history)

    async def on_focus_pane_message_submitted(self, message: FocusPane.MessageSubmitted) -> None:
        """Handle a message being submitted in the focus pane."""
        user_message = AgentInputUserMessage(content=message.text)
        await self.workflow.post_message(message=user_message, target_agent_name=message.agent_name)
