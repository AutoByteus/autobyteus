# file: autobyteus/autobyteus/agent/utils/wait_for_idle.py
import asyncio
import logging
from typing import Optional

from autobyteus.agent.agent import Agent
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.agent.streaming.stream_events import StreamEventType
from autobyteus.agent.phases import AgentOperationalPhase

logger = logging.getLogger(__name__)

async def _wait_loop(streamer: AgentEventStream, agent_id: str):
    """Internal helper to listen for the IDLE or ERROR event."""
    async for event in streamer.all_events():
        if event.event_type == StreamEventType.AGENT_IDLE:
            logger.info(f"Agent '{agent_id}' has become idle.")
            return
        if event.event_type == StreamEventType.ERROR_EVENT:
             error_message = f"Agent '{agent_id}' entered an error state while waiting for idle: {event.data}"
             logger.error(error_message)
             raise RuntimeError(error_message)


async def wait_for_agent_to_be_idle(agent: Agent, timeout: float = 30.0):
    """
    Waits for an agent to complete its bootstrapping and enter the IDLE state.

    This is useful after starting an agent to ensure it is fully initialized and
    ready to process requests before sending the first one.

    Args:
        agent: The agent instance to monitor.
        timeout: The maximum time in seconds to wait. Defaults to 30.0.

    Raises:
        asyncio.TimeoutError: If the agent does not become idle within the timeout period.
        RuntimeError: If the agent enters an error state while waiting to become idle.
        TypeError: If the 'agent' argument is not an instance of the Agent class.
    """
    if not isinstance(agent, Agent):
        raise TypeError("The 'agent' argument must be an instance of the Agent class.")

    current_phase = agent.get_current_phase()
    if current_phase.is_terminal():
        logger.warning(f"Agent '{agent.agent_id}' is already in a terminal state ({current_phase.value}) and will not become idle.")
        return

    if current_phase == AgentOperationalPhase.IDLE:
        logger.debug(f"Agent '{agent.agent_id}' is already idle.")
        return

    logger.info(f"Waiting for agent '{agent.agent_id}' to become idle (timeout: {timeout}s)...")
    
    streamer = AgentEventStream(agent)
    try:
        await asyncio.wait_for(_wait_loop(streamer, agent.agent_id), timeout=timeout)
    finally:
        await streamer.close()
