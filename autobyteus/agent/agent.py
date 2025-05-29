# file: autobyteus/autobyteus/agent/agent.py
import asyncio
import logging
from typing import AsyncIterator, Optional, List, Any, Dict, TYPE_CHECKING

from autobyteus.agent.agent_runtime import AgentRuntime
# from autobyteus.agent.status import AgentStatus # REMOVED, use AgentOperationalPhase
from autobyteus.agent.phases import AgentOperationalPhase # ADDED
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.agent.events import UserMessageReceivedEvent, InterAgentMessageReceivedEvent, ToolExecutionApprovalEvent

if TYPE_CHECKING:
    from autobyteus.agent.events import AgentEventQueues
    from autobyteus.agent.context import AgentContext 


logger = logging.getLogger(__name__)

class Agent:
    """
    User-facing API for interacting with an agent's runtime.
    It manages an underlying AgentRuntime instance and translates user actions
    into events for the agent's event processing loop.
    """

    def __init__(self, runtime: AgentRuntime):
        if not isinstance(runtime, AgentRuntime): # pragma: no cover
            raise TypeError(f"Agent requires an AgentRuntime instance, got {type(runtime).__name__}")
        
        self._runtime: AgentRuntime = runtime
        self.context: 'AgentContext' = runtime.context 
        self.agent_id: str = self.context.agent_id 
        
        logger.info(f"Agent facade initialized for agent_id '{self.agent_id}'.")

    async def post_user_message(self, agent_input_user_message: AgentInputUserMessage) -> None:
        if not isinstance(agent_input_user_message, AgentInputUserMessage): # pragma: no cover
            raise TypeError(f"Agent for '{self.agent_id}' received invalid type for user_message. Expected AgentInputUserMessage, got {type(agent_input_user_message)}.")

        if not self._runtime.is_running: # pragma: no cover
            logger.info(f"Agent '{self.agent_id}' runtime is not running. Calling start() before posting message.")
            self.start()
            await asyncio.sleep(0.01) 
        
        event = UserMessageReceivedEvent(agent_input_user_message=agent_input_user_message)
        await self.context.queues.enqueue_user_message(event)
        logger.debug(f"Agent '{self.agent_id}' enqueued UserMessageReceivedEvent.")

    async def post_inter_agent_message(self, inter_agent_message: InterAgentMessage) -> None:
        if not isinstance(inter_agent_message, InterAgentMessage): # pragma: no cover
            raise TypeError(
                f"Agent for '{self.agent_id}' received invalid type for inter_agent_message. "
                f"Expected InterAgentMessage, got {type(inter_agent_message).__name__}."
            )

        if not self._runtime.is_running: # pragma: no cover
            logger.info(f"Agent '{self.agent_id}' runtime is not running. Calling start() before posting inter-agent message.")
            self.start()
            await asyncio.sleep(0.01)
        
        event = InterAgentMessageReceivedEvent(inter_agent_message=inter_agent_message)
        await self.context.queues.enqueue_inter_agent_message(event)
        logger.debug(f"Agent '{self.agent_id}' enqueued InterAgentMessageReceivedEvent for sender '{inter_agent_message.sender_agent_id}'.")


    async def post_tool_execution_approval(self,
                                         tool_invocation_id: str,
                                         is_approved: bool,
                                         reason: Optional[str] = None) -> None:
        if not isinstance(tool_invocation_id, str) or not tool_invocation_id: # pragma: no cover
             raise ValueError("tool_invocation_id must be a non-empty string.")
        if not isinstance(is_approved, bool): # pragma: no cover
            raise TypeError("is_approved must be a boolean.")

        if not self._runtime.is_running: # pragma: no cover
            logger.info(f"Agent '{self.agent_id}' runtime is not running. Calling start() before posting tool approval/denial.")
            self.start()
            await asyncio.sleep(0.01)

        approval_event = ToolExecutionApprovalEvent(
            tool_invocation_id=tool_invocation_id,
            is_approved=is_approved,
            reason=reason
        )
        await self.context.queues.enqueue_tool_approval_event(approval_event)
        status_str = "approved" if is_approved else "denied"
        logger.debug(f"Agent '{self.agent_id}' enqueued ToolExecutionApprovalEvent for id '{tool_invocation_id}' ({status_str}).")

    def get_event_queues(self) -> 'AgentEventQueues': # pragma: no cover
        logger.debug(f"Agent '{self.agent_id}' providing access to AgentEventQueues (via context.state.queues).")
        return self.context.queues 

    def get_current_phase(self) -> AgentOperationalPhase: # MODIFIED
        return self._runtime.current_phase_property 
    
    @property
    def is_running(self) -> bool:
        return self._runtime.is_running

    def start(self) -> None:
        if self._runtime.is_running: # pragma: no cover
            logger.info(f"Agent '{self.agent_id}' runtime is already running. Ignoring start command.")
            return
            
        logger.info(f"Agent '{self.agent_id}' requesting runtime to start.")
        self._runtime.start_execution_loop()

    async def stop(self, timeout: float = 10.0) -> None: # pragma: no cover
        logger.info(f"Agent '{self.agent_id}' requesting runtime to stop (timeout: {timeout}s).")
        await self._runtime.stop_execution_loop(timeout=timeout)


    def __repr__(self) -> str:
        phase_val = self._runtime.current_phase_property.value 
        return f"<Agent agent_id='{self.agent_id}', current_phase='{phase_val}'>"

