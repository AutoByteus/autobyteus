# file: autobyteus/autobyteus/cli/agent_team_tui/app.py
"""
The main Textual application class for the agent team TUI. This class orchestrates
the UI by reacting to changes in a central state store.
"""
import asyncio
import logging
from typing import Dict, Optional, Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Static
from textual.reactive import reactive

from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent_team.streaming.agent_team_event_stream import AgentTeamEventStream
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.stream_events import StreamEventType as AgentStreamEventType
from autobyteus.agent.streaming.stream_event_payloads import AssistantChunkData
from autobyteus.agent_team.streaming.agent_team_stream_event_payloads import AgentEventRebroadcastPayload, AgentTeamPhaseTransitionData

from .state import TUIStateStore
from .widgets.agent_list_sidebar import AgentListSidebar
from .widgets.focus_pane import FocusPane
from .widgets.status_bar import StatusBar

logger = logging.getLogger(__name__)

class AgentTeamApp(App):
    """A Textual TUI for interacting with an agent team, built around a central state store."""

    TITLE = "AutoByteus"
    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("q", "quit", "Quit"),
    ]

    focused_node_data: reactive[Optional[Dict[str, Any]]] = reactive(None)
    # The store_version property will trigger UI updates for the sidebar.
    store_version: reactive[int] = reactive(0)

    def __init__(self, team: AgentTeam, **kwargs):
        super().__init__(**kwargs)
        self.team = team
        self.store = TUIStateStore(team=self.team)
        self.team_stream: Optional[AgentTeamEventStream] = None
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
        self.team.start()
        self.team_stream = AgentTeamEventStream(self.team)
        
        # Initialize the UI with the starting state
        initial_tree = self.store.get_tree_data()
        initial_focus_node = initial_tree.get(self.team.name)
        
        self.store.set_focused_node(initial_focus_node)
        self.focused_node_data = initial_focus_node
        self.store_version = self.store.version # Trigger initial render
        
        self.run_worker(self._listen_for_team_events(), name="team_listener")
        
        # Set up a timer to run the throttled UI updater at ~15 FPS.
        self.set_interval(1 / 15, self._throttled_ui_updater, name="ui_updater")
        logger.info("Agent Team TUI mounted, team listener and throttled UI updater started.")

    async def on_unmount(self) -> None:
        if self.team and self.team.is_running:
            await self.team.stop()

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

    async def _listen_for_team_events(self) -> None:
        """A background worker that forwards team events to the state store and updates the UI."""
        if not self.team_stream: return
        try:
            async for event in self.team_stream.all_events():
                # 1. Always update the central state store immediately.
                self.store.process_event(event)
                
                # 2. Mark the UI as needing an update for the throttled components.
                self._ui_update_pending = True
                
                # 3. Handle real-time, incremental updates directly.
                if isinstance(event.data, AgentEventRebroadcastPayload):
                    payload = event.data
                    agent_name = payload.agent_name
                    agent_event = payload.agent_event
                    focus_pane = self.query_one(FocusPane)
                    
                    is_currently_focused = (focus_pane._focused_node_data and focus_pane._focused_node_data.get('name') == agent_name)

                    if is_currently_focused:
                        await focus_pane.add_agent_event(agent_event)

        except asyncio.CancelledError:
            logger.info("Agent team event listener task was cancelled.")
        except Exception:
            logger.error("Critical error in agent team TUI event listener", exc_info=True)
        finally:
            if self.team_stream: await self.team_stream.close()

    # --- Reactive Watchers ---

    async def watch_store_version(self, new_version: int):
        """
        Reacts to changes in the store version.
        """
        sidebar = self.query_one(AgentListSidebar)
        focus_pane = self.query_one(FocusPane)

        tree_data = self.store.get_tree_data()
        agent_phases = self.store._agent_phases
        team_phases = self.store._team_phases
        speaking_agents = self.store._speaking_agents
        
        sidebar.update_tree(tree_data, agent_phases, team_phases, speaking_agents)
        
        focused_data = self.focused_node_data
        if focused_data and focused_data.get("type") in ['team', 'subteam']:
            node_name = focused_data['name']
            task_plan = self.store.get_task_board_plan(node_name)
            task_statuses = self.store.get_task_board_statuses(node_name)
            await focus_pane.update_content(
                node_data=focused_data,
                history=[], # No history for teams
                pending_approval=None,
                all_agent_phases=agent_phases,
                all_team_phases=team_phases,
                task_plan=task_plan,
                task_statuses=task_statuses
            )
        elif focused_data and focused_data.get("type") == 'agent':
            focus_pane.update_current_node_status(agent_phases, team_phases)


    async def watch_focused_node_data(self, new_node_data: Optional[Dict[str, Any]]):
        """Reacts to changes in which node is focused. Primarily used for full pane reloads on user click."""
        if not new_node_data: return
        
        node_name = new_node_data['name']
        node_type = new_node_data['type']

        history = self.store.get_history_for_node(node_name, node_type)
        pending_approval = self.store.get_pending_approval_for_agent(node_name) if node_type == 'agent' else None
        
        task_plan = None
        task_statuses = None
        if node_type in ['team', 'subteam']:
            task_plan = self.store.get_task_board_plan(node_name)
            task_statuses = self.store.get_task_board_statuses(node_name)
        
        sidebar = self.query_one(AgentListSidebar)
        focus_pane = self.query_one(FocusPane)
        
        await focus_pane.update_content(
            node_data=new_node_data,
            history=history,
            pending_approval=pending_approval,
            all_agent_phases=self.store._agent_phases,
            all_team_phases=self.store._team_phases,
            task_plan=task_plan,
            task_statuses=task_statuses
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
        await self.team.post_message(message=user_message, target_agent_name=message.agent_name)

    async def on_focus_pane_approval_submitted(self, message: FocusPane.ApprovalSubmitted):
        """Dispatches a tool approval to the backend model."""
        self.store.clear_pending_approval(message.agent_name)
        await self.team.post_tool_execution_approval(
            agent_name=message.agent_name,
            tool_invocation_id=message.invocation_id,
            is_approved=message.is_approved,
            reason=message.reason,
        )
