# file: autobyteus/autobyteus/cli/workflow_tui/widgets/shared.py
"""
Shared constants and data for TUI widgets.
"""
from typing import Dict
from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.workflow.status.workflow_status import WorkflowStatus

AGENT_STATUS_ICONS: Dict[AgentStatus, str] = {
    AgentStatus.UNINITIALIZED: "⚪",
    AgentStatus.BOOTSTRAPPING: "⏳",
    AgentStatus.IDLE: "🟢",
    AgentStatus.PROCESSING_USER_INPUT: "💭",
    AgentStatus.AWAITING_LLM_RESPONSE: "💭",
    AgentStatus.ANALYZING_LLM_RESPONSE: "🤔",
    AgentStatus.AWAITING_TOOL_APPROVAL: "❓",
    AgentStatus.TOOL_DENIED: "❌",
    AgentStatus.EXECUTING_TOOL: "🛠️",
    AgentStatus.PROCESSING_TOOL_RESULT: "⚙️",
    AgentStatus.SHUTTING_DOWN: "🌙",
    AgentStatus.SHUTDOWN_COMPLETE: "⚫",
    AgentStatus.ERROR: "❗",
}

WORKFLOW_STATUS_ICONS: Dict[WorkflowStatus, str] = {
    WorkflowStatus.UNINITIALIZED: "⚪",
    WorkflowStatus.BOOTSTRAPPING: "⏳",
    WorkflowStatus.IDLE: "🟢",
    WorkflowStatus.PROCESSING: "⚙️",
    WorkflowStatus.SHUTTING_DOWN: "🌙",
    WorkflowStatus.SHUTDOWN_COMPLETE: "⚫",
    WorkflowStatus.ERROR: "❗",
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
STATUS_ICON = "🔄"
LOG_ICON = "📄"
