"""
Shared constants and data for TUI widgets.
"""
from typing import Dict
from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.agent_team.phases import AgentTeamOperationalPhase
from autobyteus.task_management.base_task_board import TaskStatus

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

TEAM_PHASE_ICONS: Dict[AgentTeamOperationalPhase, str] = {
    AgentTeamOperationalPhase.UNINITIALIZED: "⚪",
    AgentTeamOperationalPhase.BOOTSTRAPPING: "⏳",
    AgentTeamOperationalPhase.IDLE: "🟢",
    AgentTeamOperationalPhase.PROCESSING: "⚙️",
    AgentTeamOperationalPhase.SHUTTING_DOWN: "🌙",
    AgentTeamOperationalPhase.SHUTDOWN_COMPLETE: "⚫",
    AgentTeamOperationalPhase.ERROR: "❗",
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
PHASE_ICON = "🔄"
LOG_ICON = "📄"
SYSTEM_TASK_ICON = "📥" # NEW
