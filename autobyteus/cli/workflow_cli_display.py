# file: autobyteus/autobyteus/cli/workflow_cli_display.py
import asyncio
import logging
import sys
import textwrap

from ..agent.workflow.streaming.workflow_stream_events import WorkflowStreamEvent, WorkflowStreamEventType
from ..agent.workflow.streaming.workflow_stream_event_payloads import (
    WorkflowPhaseTransitionData,
    AgentActivityLogData,
    WorkflowFinalResultData,
)
from ..agent.streaming.stream_events import StreamEvent as AgentStreamEvent, StreamEventType as AgentStreamEventType
from ..agent.streaming.stream_event_payloads import AssistantChunkData, ToolInteractionLogEntryData
from ..agent.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase

logger = logging.getLogger(__name__)

class InteractiveWorkflowCLIDisplay:
    """Manages the state and rendering for the interactive workflow CLI."""
    def __init__(self, workflow_turn_complete_event: asyncio.Event):
        self.workflow_turn_complete_event = workflow_turn_complete_event
        self.current_line_empty = True
        self._agent_displays: dict[str, dict] = {}

    def _get_agent_display_state(self, agent_name: str) -> dict:
        if agent_name not in self._agent_displays:
            self._agent_displays[agent_name] = {
                "is_thinking": False,
                "has_spoken": False,
                "color_code": "\x1b[32m" # Green for coordinator
            }
            if len(self._agent_displays) > 1: # Assign different colors to other agents
                colors = ["\x1b[33m", "\x1b[35m", "\x1b[34m"] # Yellow, Magenta, Blue
                self._agent_displays[agent_name]["color_code"] = colors[(len(self._agent_displays)-2) % len(colors)]
        return self._agent_displays[agent_name]

    def _ensure_new_line(self):
        if not self.current_line_empty:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self.current_line_empty = True

    def _render_agent_event(self, agent_name: str, agent_event: AgentStreamEvent):
        state = self._get_agent_display_state(agent_name)
        color = state["color_code"]
        end_color = "\x1b[0m"
        indent = "    " if len(self._agent_displays) > 1 and not state.get("is_coordinator") else ""

        if agent_event.event_type == AgentStreamEventType.ASSISTANT_CHUNK:
            data: AssistantChunkData = agent_event.data
            if data.reasoning:
                if not state["is_thinking"]:
                    print(f"{indent}{color}[{agent_name} | Thinking]:{end_color}", file=sys.stderr)
                    state["is_thinking"] = True
                print(textwrap.indent(data.reasoning, f"{indent}  "), end="", file=sys.stderr)
            if data.content:
                if state["is_thinking"]: # End thinking block
                    print(file=sys.stderr)
                    state["is_thinking"] = False
                if not state["has_spoken"]:
                    print(f"{indent}{color}[{agent_name} | Speaking]:{end_color}")
                    state["has_spoken"] = True
                print(textwrap.indent(data.content, f"{indent}  "), end="")
        
        elif agent_event.event_type == AgentStreamEventType.TOOL_INTERACTION_LOG_ENTRY:
            data: ToolInteractionLogEntryData = agent_event.data
            log_color = "\x1b[90m" # Grey
            print(f"{indent}{log_color}[{agent_name} | Tool Log]: {data.log_entry}{end_color}", file=sys.stderr)
        
        elif agent_event.event_type == AgentStreamEventType.ASSISTANT_COMPLETE_RESPONSE:
            state["is_thinking"] = False
            state["has_spoken"] = False # Reset for next turn

    async def handle_stream_event(self, event: WorkflowStreamEvent):
        self._ensure_new_line()

        if event.event_type == WorkflowStreamEventType.WORKFLOW_PHASE_TRANSITION:
            data: WorkflowPhaseTransitionData = event.data
            logger.info(f"[Workflow Status: {data.new_phase.value}]")
            if data.new_phase in [WorkflowOperationalPhase.IDLE, WorkflowOperationalPhase.ERROR]:
                self.workflow_turn_complete_event.set()

        elif event.event_type == WorkflowStreamEventType.AGENT_ACTIVITY_LOG:
            data: AgentActivityLogData = event.data
            if isinstance(data.agent_event, AgentStreamEvent):
                # This is a rebroadcasted agent event, render it with context
                self._render_agent_event(data.agent_name, data.agent_event)
            else:
                # This is a simple string activity log
                log_color = "\x1b[36m" # Cyan
                log_message = f"{log_color}[Team Activity: {data.agent_name} -> {data.agent_event}]{end_color}"
                print(log_message, file=sys.stderr)

        elif event.event_type == WorkflowStreamEventType.WORKFLOW_FINAL_RESULT:
            data: WorkflowFinalResultData = event.data
            print("\n" + "="*25 + " WORKFLOW FINAL RESULT " + "="*25)
            print(data.result)
            print("="*72)
            self.current_line_empty = True
