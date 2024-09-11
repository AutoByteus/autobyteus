import asyncio
import logging
from autobyteus.agent.agent import StandaloneAgent, AgentStatus
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.events.event_types import EventType
from autobyteus.agent.message.message_types import MessageType
from autobyteus.agent.message.message import Message
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from autobyteus.agent.orchestrator.base_agent_orchestrator import BaseAgentOrchestrator

logger = logging.getLogger(__name__)

class GroupAwareAgent(StandaloneAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_orchestrator: Optional['BaseAgentOrchestrator'] = None
        self.incoming_agent_messages: Optional[asyncio.Queue] = None
        logger.info(f"GroupAwareAgent initialized with role: {self.role}")

    def _initialize_queues(self):
        super()._initialize_queues()
        if not hasattr(self, 'incoming_agent_messages'):
            self.incoming_agent_messages = asyncio.Queue()
        logger.info(f"Queues initialized for agent {self.role}")

    def set_agent_orchestrator(self, agent_orchestrator: 'BaseAgentOrchestrator'):
        self.agent_orchestrator = agent_orchestrator
        if not any(isinstance(tool, SendMessageTo) for tool in self.tools):
            self.tools.append(SendMessageTo(agent_orchestrator))
        logger.info(f"Agent orchestrator set for agent {self.role}")

    async def receive_agent_message(self, message: Message):
        logger.info(f"Agent {self.agent_id} received message from {message.sender_agent_id}")
        await self.incoming_agent_messages.put(message)
        if self.status != AgentStatus.RUNNING:
            self.start()

    async def run(self):
        try:
            logger.info(f"Agent {self.role} entering running state")
            self._initialize_queues()
            self._initialize_task_completed()
            await self.initialize_llm_conversation()
            
            # Send initial prompt as a user message
            initial_prompt = self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section()).build()
            await self.user_messages.put(initial_prompt)
            
            self.status = AgentStatus.RUNNING
            
            user_message_handler = asyncio.create_task(self.handle_user_messages())
            tool_result_handler = asyncio.create_task(self.handle_tool_result_messages())
            agent_message_handler = asyncio.create_task(self.handle_agent_messages())
            
            await asyncio.gather(user_message_handler, tool_result_handler, agent_message_handler)

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
                
                llm_response = await self.conversation.send_user_message(f"Message from sender_agent_id {message.sender_agent_id}, content {message.content}")
                await self.process_llm_response(llm_response)
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
        logger.info(f"Cleanup completed for group-aware agent: {self.role}")
