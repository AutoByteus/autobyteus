# file: autobyteus/autobyteus/agent_team/agent_team.py
import logging
from typing import Optional

from autobyteus.agent_team.runtime.agent_team_runtime import AgentTeamRuntime
from autobyteus.agent_team.events.agent_team_events import ProcessUserMessageEvent, ToolApprovalTeamEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent_team.phases.agent_team_operational_phase import AgentTeamOperationalPhase

logger = logging.getLogger(__name__)

class AgentTeam:
    """
    User-facing facade for interacting with a managed agent team.
    This class is a lightweight wrapper around an AgentTeamRuntime instance
    and is typically created by an AgentTeamFactory.
    """
    def __init__(self, runtime: AgentTeamRuntime):
        """
        Initializes the AgentTeam facade.

        Args:
            runtime: The pre-configured and ready-to-use runtime for the agent team.
        """
        if not isinstance(runtime, AgentTeamRuntime):
            raise TypeError(f"AgentTeam requires an AgentTeamRuntime instance, got {type(runtime).__name__}")
        
        self._runtime = runtime
        self.team_id: str = self._runtime.context.team_id
        logger.info(f"AgentTeam facade created for team ID '{self.team_id}'.")

    @property
    def name(self) -> str:
        return self._runtime.context.config.name

    @property
    def role(self) -> Optional[str]:
        """The role of the team, for when it's used as a sub-team."""
        return self._runtime.context.config.role

    async def post_message(self, message: AgentInputUserMessage, target_agent_name: Optional[str] = None) -> None:
        """
        Submits a message to the agent team, routing it to a specific node (agent or sub-team).
        If `target_agent_name` is not provided, the message is sent to the team's coordinator.
        """
        final_target_name = target_agent_name or self._runtime.context.config.coordinator_node.name
        logger.info(f"Agent Team '{self.team_id}': post_message called. Target: '{final_target_name}'.")

        if not self._runtime.is_running:
            self.start()
        
        event = ProcessUserMessageEvent(
            user_message=message,
            target_agent_name=final_target_name
        )
        await self._runtime.submit_event(event)

    async def post_tool_execution_approval(
        self,
        agent_name: str,
        tool_invocation_id: str,
        is_approved: bool,
        reason: Optional[str] = None
    ):
        """Submits a tool execution approval/denial to a specific agent in the team."""
        logger.info(f"Agent Team '{self.team_id}': post_tool_execution_approval called for agent '{agent_name}'. Approved: {is_approved}.")
        if not self._runtime.is_running:
            logger.warning(f"Agent Team '{self.team_id}' is not running. Cannot post approval.")
            return

        event = ToolApprovalTeamEvent(
            agent_name=agent_name,
            tool_invocation_id=tool_invocation_id,
            is_approved=is_approved,
            reason=reason,
        )
        await self._runtime.submit_event(event)

    def start(self) -> None:
        """Starts the agent team's background worker thread."""
        self._runtime.start()

    async def stop(self, timeout: float = 10.0) -> None:
        """Stops the agent team and all its agents."""
        await self._runtime.stop(timeout)

    @property
    def is_running(self) -> bool:
        """Checks if the agent team's worker is running."""
        return self._runtime.is_running
        
    def get_current_phase(self) -> AgentTeamOperationalPhase: 
        return self._runtime.context.state.current_phase
