# file: autobyteus/autobyteus/agent_team/utils/wait_for_idle.py
import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.streaming.agent_team_event_stream import AgentTeamEventStream
from autobyteus.agent_team.phases.agent_team_operational_phase import AgentTeamOperationalPhase

if TYPE_CHECKING:
    from autobyteus.agent_team.agent_team import AgentTeam

logger = logging.getLogger(__name__)

async def _wait_loop(streamer: AgentTeamEventStream, team_id: str):
    """Internal helper to listen for the IDLE or ERROR event."""
    async for event in streamer.all_events():
        if event.event_source_type == "TEAM" and event.data.new_phase == AgentTeamOperationalPhase.IDLE:
            logger.info(f"Team '{team_id}' has become idle.")
            return
        if event.event_source_type == "TEAM" and event.data.new_phase == AgentTeamOperationalPhase.ERROR:
             error_message = f"Team '{team_id}' entered an error state while waiting for idle: {event.data.error_message}"
             logger.error(error_message)
             raise RuntimeError(error_message)

async def wait_for_team_to_be_idle(team: 'AgentTeam', timeout: float = 60.0):
    """
    Waits for an agent team to complete its bootstrapping and enter the IDLE state.

    Args:
        team: The agent team instance to monitor.
        timeout: The maximum time in seconds to wait.

    Raises:
        asyncio.TimeoutError: If the team does not become idle within the timeout period.
        RuntimeError: If the team enters an error state.
    """
    if team.get_current_phase() == AgentTeamOperationalPhase.IDLE:
        return
    
    logger.info(f"Waiting for team '{team.team_id}' to become idle (timeout: {timeout}s)...")
    
    streamer = AgentTeamEventStream(team)
    try:
        await asyncio.wait_for(_wait_loop(streamer, team.team_id), timeout=timeout)
    finally:
        await streamer.close()
