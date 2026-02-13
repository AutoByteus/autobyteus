# file: autobyteus/autobyteus/agent/status/status_deriver.py
import logging
from typing import Optional, Tuple, TYPE_CHECKING

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.events.agent_events import (
    AgentReadyEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    AgentIdleEvent,
    ShutdownRequestedEvent,
    BootstrapStartedEvent,
    BootstrapCompletedEvent,
    UserMessageReceivedEvent,
    InterAgentMessageReceivedEvent,
    LLMUserMessageReadyEvent,
    LLMCompleteResponseReceivedEvent,
    PendingToolInvocationEvent,
    ToolExecutionApprovalEvent,
    ExecuteToolInvocationEvent,
    ToolResultEvent,
)

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.agent_events import BaseEvent

logger = logging.getLogger(__name__)


class AgentStatusDeriver:
    """
    Derives agent status from an event stream.
    This is a pure read-model: no side effects beyond status updates.
    """
    def __init__(self, initial_status: AgentStatus = AgentStatus.UNINITIALIZED):
        self._current_status = initial_status
        logger.debug(f"AgentStatusDeriver initialized with status '{initial_status.value}'.")

    @property
    def current_status(self) -> AgentStatus:
        return self._current_status

    def apply(self, event: 'BaseEvent', context: Optional['AgentContext'] = None) -> Tuple[AgentStatus, AgentStatus]:
        old_status = self._current_status
        new_status = self._reduce(event, old_status, context)
        self._current_status = new_status
        return old_status, new_status

    def _reduce(self, event: 'BaseEvent', current_status: AgentStatus, context: Optional['AgentContext']) -> AgentStatus:
        if isinstance(event, BootstrapStartedEvent):
            return AgentStatus.BOOTSTRAPPING
        if isinstance(event, BootstrapCompletedEvent):
            return current_status
        if isinstance(event, AgentReadyEvent):
            return AgentStatus.IDLE
        if isinstance(event, AgentIdleEvent):
            return AgentStatus.IDLE
        if isinstance(event, ShutdownRequestedEvent):
            if current_status == AgentStatus.ERROR:
                return current_status
            return AgentStatus.SHUTTING_DOWN
        if isinstance(event, AgentStoppedEvent):
            if current_status == AgentStatus.ERROR:
                return AgentStatus.ERROR
            return AgentStatus.SHUTDOWN_COMPLETE
        if isinstance(event, AgentErrorEvent):
            return AgentStatus.ERROR

        if isinstance(event, (UserMessageReceivedEvent, InterAgentMessageReceivedEvent)):
            return AgentStatus.PROCESSING_USER_INPUT
        if isinstance(event, LLMUserMessageReadyEvent):
            if current_status in [AgentStatus.AWAITING_LLM_RESPONSE, AgentStatus.ERROR]:
                return current_status
            return AgentStatus.AWAITING_LLM_RESPONSE
        if isinstance(event, LLMCompleteResponseReceivedEvent):
            if current_status != AgentStatus.AWAITING_LLM_RESPONSE:
                return current_status
            return AgentStatus.ANALYZING_LLM_RESPONSE

        if isinstance(event, PendingToolInvocationEvent):
            if context and not context.auto_execute_tools:
                return AgentStatus.AWAITING_TOOL_APPROVAL
            return AgentStatus.EXECUTING_TOOL
        if isinstance(event, ExecuteToolInvocationEvent):
            return AgentStatus.EXECUTING_TOOL
        if isinstance(event, ToolExecutionApprovalEvent):
            if event.is_approved:
                return AgentStatus.EXECUTING_TOOL
            return AgentStatus.TOOL_DENIED
        if isinstance(event, ToolResultEvent):
            if current_status != AgentStatus.EXECUTING_TOOL:
                return current_status
            return AgentStatus.PROCESSING_TOOL_RESULT

        return current_status
