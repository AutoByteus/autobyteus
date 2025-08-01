# file: autobyteus/autobyteus/cli/workflow_tui/widgets/shared.py
"""
Shared constants and data for TUI widgets.
"""
from typing import Dict
from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.workflow.phases import WorkflowOperationalPhase

AGENT_PHASE_ICONS: Dict[AgentOperationalPhase, str] = {
    AgentOperationalPhase.UNINITIALIZED: "⚪",
    AgentOperationalPhase.BOOTSTRAPPING: "⏳",
    AgentOperationalPhase.IDLE: "🟢",
    AgentOperationalPhase.PROCESSING_USER_INPUT: "💭",
    AgentOperationalPhase.AWAITING_LLM_RESPONSE: "💭",
    AgentOperationalPhase.ANALYZING_LLM_RESPONSE: "🤔",
    AgentOperationalPhase.AWAITING_TOOL_APPROVAL: "❓",
    AgentOperationalPhase.TOOL_DENIED: "❌",
    AgentOperationalPhase.EXECUTING_TOOL: "🛠️",
    AgentOperationalPhase.PROCESSING_TOOL_RESULT: "⚙️",
    AgentOperationalPhase.SHUTTING_DOWN: "🌙",
    AgentOperationalPhase.SHUTDOWN_COMPLETE: "⚫",
    AgentOperationalPhase.ERROR: "❗",
}

WORKFLOW_PHASE_ICONS: Dict[WorkflowOperationalPhase, str] = {
    WorkflowOperationalPhase.UNINITIALIZED: "⚪",
    WorkflowOperationalPhase.BOOTSTRAPPING: "⏳",
    WorkflowOperationalPhase.IDLE: "🟢",
    WorkflowOperationalPhase.PROCESSING: "⚙️",
    WorkflowOperationalPhase.SHUTTING_DOWN: "🌙",
    WorkflowOperationalPhase.SHUTDOWN_COMPLETE: "⚫",
    WorkflowOperationalPhase.ERROR: "❗",
}

# Main component icons
SUB_WORKFLOW_ICON = "📂"
WORKFLOW_ICON = "🏁"
AGENT_ICON = "🤖"

# General UI icons
SPEAKING_ICON = "🔊"
DEFAULT_ICON = "❓"

# Semantic icons for log entries
USER_ICON = "👤"
ASSISTANT_ICON = "🤖"
TOOL_ICON = "🛠️"
PROMPT_ICON = "❓"
ERROR_ICON = "💥"
PHASE_ICON = "🔄"
LOG_ICON = "📄"
