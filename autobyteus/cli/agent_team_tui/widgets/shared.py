"""
Shared constants and data for TUI widgets.
"""
from typing import Dict
from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent_team.status.agent_team_status import AgentTeamStatus
from autobyteus.task_management.base_task_plan import TaskStatus

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

TEAM_STATUS_ICONS: Dict[AgentTeamStatus, str] = {
    AgentTeamStatus.UNINITIALIZED: "⚪",
    AgentTeamStatus.BOOTSTRAPPING: "⏳",
    AgentTeamStatus.IDLE: "🟢",
    AgentTeamStatus.PROCESSING: "⚙️",
    AgentTeamStatus.SHUTTING_DOWN: "🌙",
    AgentTeamStatus.SHUTDOWN_COMPLETE: "⚫",
    AgentTeamStatus.ERROR: "❗",
}

TASK_STATUS_ICONS: Dict[TaskStatus, str] = {
    TaskStatus.NOT_STARTED: "⚪",
    TaskStatus.IN_PROGRESS: "⏳",
    TaskStatus.COMPLETED: "✅",
    TaskStatus.FAILED: "❌",
    TaskStatus.BLOCKED: "🔒",
}

# Main component icons
SUB_TEAM_ICON = "📂"
TEAM_ICON = "🏁"
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
SYSTEM_TASK_ICON = "📥" # NEW
