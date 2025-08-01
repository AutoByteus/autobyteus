# file: autobyteus/autobyteus/cli/workflow_tui/app.py
"""
The main Textual application class for the workflow TUI. This class orchestrates
the UI by reacting to changes in a central state store.
"""
import asyncio
import logging
from typing import Dict, Optional, Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Static
from textual.reactive import reactive

from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.workflow.streaming.workflow_event_stream import WorkflowEventStream
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.stream_events import StreamEventType as AgentStreamEventType
from autobyteus.agent.streaming.stream_event_payloads import AssistantChunkData
from autobyteus.workflow.streaming.workflow_stream_event_payloads import AgentEventRebroadcastPayload, WorkflowPhaseTransitionData

from .state import TUIStateStore
from .widgets.agent_list_sidebar import AgentListSidebar
from .widgets.focus_pane import FocusPane
from .widgets.status_bar import StatusBar

logger = logging.getLogger(__name__)

class WorkflowApp(App):
    """A Textual TUI for interacting with an agentic workflow, built around a central state store."""

    TITLE = "AutoByteus"
    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("q", "quit", "Quit"),
    ]

    focused_node_data: reactive[Optional[Dict[str, Any]]] = reactive(None)
    # The store_version property will trigger UI updates for the sidebar.
    store_version: reactive[int] = reactive(0)

    def __init__(self, workflow: AgenticWorkflow, **kwargs):
        super().__init__(**kwargs)
        self.workflow = workflow
        self.store = TUIStateStore(workflow=self.workflow)
        self.workflow_stream: Optional[WorkflowEventStream] = None
        # Flag to indicate that the UI needs an update, used for throttling.
        self._ui_update_pending = False

    def compose(self) -> ComposeResult:
        yield Header(id="app-header", name="AutoByteus Mission Control")
        with Horizontal(id="main-container"):
            yield AgentListSidebar(id="sidebar")
            yield FocusPane(id="focus-pane")
        yield StatusBar()

    async def on_mount(self) -> None:
        """Start background tasks when the app is mounted."""
        self.workflow.start()
        self.workflow_stream = WorkflowEventStream(self.workflow)
        
        # Initialize the UI with the starting state
        initial_tree = self.store.get_tree_data()
        initial_focus_node = initial_tree.get(self.workflow.name)
        
        self.store.set_focused_node(initial_focus_node)
        self.focused_node_data = initial_focus_node
        self.store_version = self.store.version # Trigger initial render
        
        self.run_worker(self._listen_for_workflow_events(), name="workflow_listener")
        
        # Set up a timer to run the throttled UI updater at ~15 FPS.
        self.set_interval(1 / 15, self._throttled_ui_updater, name="ui_updater")
        logger.info("Workflow TUI mounted, workflow listener and throttled UI updater started.")

    async def on_unmount(self) -> None:
        if self.workflow and self.workflow.is_running:
            await self.workflow.stop()

    def _throttled_ui_updater(self) -> None:
        """
        Periodically checks if the UI state is dirty and, if so, triggers
        reactive updates. It also flushes streaming buffers from the focus pane.
        """
        focus_pane = self.query_one(FocusPane)
        if self._ui_update_pending:
            self._ui_update_pending = False
            # This is the throttled trigger for the async watcher.
            self.store_version = self.store.version
        
        # Always flush the focus pane's streaming buffer for smooth text rendering.
        focus_pane.flush_stream_buffers()

    async def _listen_for_workflow_events(self) -> None:
        """A background worker that forwards workflow events to the state store and updates the UI."""
        if not self.workflow_stream: return
        try:
            async for event in self.workflow_stream.all_events():
                # 1. Always update the central state store immediately.
                self.store.process_event(event)
                
                # 2. Mark the UI as needing an update for the throttled components.
                self._ui_update_pending = True
                
                # 3. Handle real-time, incremental updates directly.
                # This is for components like the FocusPane's text stream, which needs
                # to be as low-latency as possible. The actual UI update is buffered.
                if isinstance(event.data, AgentEventRebroadcastPayload):
                    payload = event.data
                    agent_name = payload.agent_name
                    agent_event = payload.agent_event
                    focus_pane = self.query_one(FocusPane)
                    
                    is_currently_focused = (focus_pane._focused_node_data and focus_pane._focused_node_data.get('name') == agent_name)

                    # If the event is for the currently focused agent, send the event
                    # to be buffered and eventually rendered.
                    if is_currently_focused:
                        await focus_pane.add_agent_event(agent_event)

        except asyncio.CancelledError:
            logger.info("Workflow event listener task was cancelled.")
        except Exception:
            logger.error("Critical error in workflow TUI event listener", exc_info=True)
        finally:
            if self.workflow_stream: await self.workflow_stream.close()

    # --- Reactive Watchers ---

    async def watch_store_version(self, new_version: int):
        """
        Reacts to changes in the store version. This is now called by the throttled
        updater, not on every event. Its main job is to update less-frequently
        changing components like the sidebar tree and workflow dashboards.
        """
        sidebar = self.query_one(AgentListSidebar)
        focus_pane = self.query_one(FocusPane)

        # Fetch fresh data from the store for the update
        tree_data = self.store.get_tree_data()
        agent_phases = self.store._agent_phases
        workflow_phases = self.store._workflow_phases
        speaking_agents = self.store._speaking_agents
        
        # Update sidebar
        sidebar.update_tree(tree_data, agent_phases, workflow_phases, speaking_agents)
        
        # Intelligently update the focus pane
        focused_data = self.focused_node_data
        if focused_data and focused_data.get("type") in ['workflow', 'subworkflow']:
            # If a workflow/subworkflow is focused, its dashboard might be out of date.
            # A full re-render is cheap and ensures consistency for its title and panels.
            history = self.store.get_history_for_node(focused_data['name'], focused_data['type'])
            await focus_pane.update_content(
                node_data=focused_data,
                history=history,
                pending_approval=None,
                all_agent_phases=agent_phases,
                all_workflow_phases=workflow_phases
            )
        elif focused_data and focused_data.get("type") == 'agent':
            # For agents, we only need to update the title status, not the whole log.
            focus_pane.update_current_node_status(agent_phases, workflow_phases)


    async def watch_focused_node_data(self, new_node_data: Optional[Dict[str, Any]]):
        """Reacts to changes in which node is focused. Primarily used for full pane reloads on user click."""
        if not new_node_data: return
        
        node_name = new_node_data['name']
        node_type = new_node_data['type']

        history = self.store.get_history_for_node(node_name, node_type)
        pending_approval = self.store.get_pending_approval_for_agent(node_name) if node_type == 'agent' else None
        
        sidebar = self.query_one(AgentListSidebar)
        focus_pane = self.query_one(FocusPane)
        
        await focus_pane.update_content(
            node_data=new_node_data,
            history=history,
            pending_approval=pending_approval,
            all_agent_phases=self.store._agent_phases,
            all_workflow_phases=self.store._workflow_phases
        )
        
        sidebar.update_selection(node_name)

    # --- Event Handlers (Actions) ---

    def on_agent_list_sidebar_node_selected(self, message: AgentListSidebar.NodeSelected):
        """Handles a node being selected by updating the store and the app's reactive state."""
        self.store.set_focused_node(message.node_data)
        self.focused_node_data = message.node_data

    async def on_focus_pane_message_submitted(self, message: FocusPane.MessageSubmitted):
        """Dispatches a user message to the backend model."""
        user_message = AgentInputUserMessage(content=message.text)
        await self.workflow.post_message(message=user_message, target_agent_name=message.agent_name)

    async def on_focus_pane_approval_submitted(self, message: FocusPane.ApprovalSubmitted):
        """Dispatches a tool approval to the backend model."""
        self.store.clear_pending_approval(message.agent_name)
        await self.workflow.post_tool_execution_approval(
            agent_name=message.agent_name,
            tool_invocation_id=message.invocation_id,
            is_approved=message.is_approved,
            reason=message.reason,
        )
