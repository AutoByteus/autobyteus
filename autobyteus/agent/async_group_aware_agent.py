
import asyncio
import logging
from typing import TYPE_CHECKING, Optional, AsyncIterator
from autobyteus.agent.async_agent import AsyncAgent
from autobyteus.agent.message.message import Message
from autobyteus.agent.message.message_types import MessageType
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.agent.status import AgentStatus
from autobyteus.events.event_types import EventType

if TYPE_CHECKING:
    from autobyteus.agent.orchestrator.base_agent_orchestrator import BaseAgentOrchestrator

logger = logging.getLogger(__name__)

class AsyncGroupAwareAgent(AsyncAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_orchestrator: Optional['BaseAgentOrchestrator'] = None
        self.incoming_agent_messages: Optional[asyncio.Queue] = None
        logger.info(f"AsyncGroupAwareAgent initialized with role: {self.role}")

    def _initialize_queues(self):
        if not self._queues_initialized:
            super()._initialize_queues()
            self.incoming_agent_messages = asyncio.Queue()
            logger.info(f"Queues initialized for agent {self.role}")

    def set_agent_orchestrator(self, agent_orchestrator: 'BaseAgentOrchestrator'):
        self.agent_orchestrator = agent_orchestrator
        if not any(isinstance(tool, SendMessageTo) for tool in self.tools):
            self.tools.append(SendMessageTo(agent_orchestrator))
        self.register_task_completion_listener()
        logger.info(f"Agent orchestrator set for agent {self.role}")

    def register_task_completion_listener(self):
        """Register to listen for task completion events from the orchestrator specifically"""
        logger.info(f"Registering task completion listener for agent: {self.role}")
        if self.agent_orchestrator:
            self.subscribe_from(
                self.agent_orchestrator, 
                EventType.TASK_COMPLETED,
                self.on_task_completed
            )
        else:
            logger.warning(f"Cannot register task completion listener for agent {self.role}: orchestrator not set")

    async def receive_agent_message(self, message: Message):
        logger.info(f"Agent {self.agent_id} received message from {message.sender_agent_id}")
        if not self._queues_initialized:
            self._initialize_queues()
        await self.incoming_agent_messages.put(message)
        if self.status != AgentStatus.RUNNING:
            self.start()

    async def run(self):
        try:
            logger.info(f"Agent {self.role} entering running state")
            self._initialize_queues()
            self._initialize_task_completed()
            await self.initialize_conversation()
        
            self.status = AgentStatus.RUNNING
            
            user_message_handler = asyncio.create_task(self.handle_user_messages())
            tool_result_handler = asyncio.create_task(self.handle_tool_result_messages())
            agent_message_handler = asyncio.create_task(self.handle_agent_messages())
            
            done, pending = await asyncio.wait(
                [agent_message_handler, tool_result_handler, user_message_handler, self.task_completed.wait()],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            await asyncio.gather(*pending, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error in agent {self.role} execution: {str(e)}")
            self.status = AgentStatus.ERROR
        finally:
            self.status = AgentStatus.ENDED
            await self.cleanup()

    async def handle_agent_messages(self):
        logger.info(f"Agent {self.role} started handling agent messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                message = await asyncio.wait_for(self.incoming_agent_messages.get(), timeout=1.0)
                logger.info(f"{self.role} processing message from {message.sender_agent_id}")
                
                if message.message_type == MessageType.TASK_RESULT:
                    self.agent_orchestrator.handle_task_completed(message.sender_agent_id)
                
                await self.process_streaming_response(
                    self.conversation.stream_user_message(
                        f"Message from sender_agent_id {message.sender_agent_id}, content {message.content}"
                    )
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"Agent message handler for agent {self.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling agent message for agent {self.role}: {str(e)}")

    async def execute_tool(self, tool_invocation):
        name = tool_invocation.name
        arguments = tool_invocation.arguments
        logger.info(f"Agent {self.role} attempting to execute tool: {name}")

        tool = next((t for t in self.tools if t.get_name() == name), None)
        if tool:
            try:
                result = await tool.execute(**arguments)
                logger.info(f"Tool '{name}' executed successfully by agent {self.role}. Result: {result}")
                if not isinstance(tool, SendMessageTo):
                    await self.tool_result_messages.put(result)
                else:
                    logger.info(f"SendMessageTo tool executed by agent {self.role}: {result}")
            except Exception as e:
                error_message = str(e)
                logger.error(f"Error executing tool '{name}' by agent {self.role}: {error_message}")
                if not isinstance(tool, SendMessageTo):
                    await self.tool_result_messages.put(f"Error: {error_message}")
        else:
            logger.warning(f"Tool '{name}' not found for agent {self.role}.")

    async def cleanup(self):
        await super().cleanup()
        while not self.incoming_agent_messages.empty():
            self.incoming_agent_messages.get_nowait()
        logger.info(f"Cleanup completed for async group-aware agent: {self.role}")
