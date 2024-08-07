# File: autobyteus/agent/group/group_aware_agent.py

import asyncio
import logging
from enum import Enum
from autobyteus.agent.agent import StandaloneAgent
from autobyteus.agent.group.send_message_to import SendMessageTo
from autobyteus.events.event_types import EventType
from autobyteus.agent.group.message_types import Message, MessageType
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from autobyteus.agent.group.base_agent_orchestrator import BaseAgentOrchestrator

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    WAITING_FOR_RESPONSE = "waiting_for_response"
    ENDED = "ended"
    ERROR = "error"

class GroupAwareAgent(StandaloneAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_orchestrator: Optional['BaseAgentOrchestrator'] = None
        self.incoming_agent_messages: Optional[asyncio.Queue] = None
        self.tool_result_messages: Optional[asyncio.Queue] = None
        self.status = AgentStatus.NOT_STARTED
        self._run_task = None
        self._queues_initialized = False
        logger.info(f"GroupAwareAgent initialized with role: {self.role}")

    def _initialize_queues(self):
        if not self._queues_initialized:
            self.incoming_agent_messages = asyncio.Queue()
            self.tool_result_messages = asyncio.Queue()
            self._queues_initialized = True
            logger.info(f"Queues initialized for agent {self.role}")

    def get_incoming_agent_messages(self):
        if not self._queues_initialized:
            raise RuntimeError("Queues accessed before initialization")
        return self.incoming_agent_messages

    def get_tool_result_messages(self):
        if not self._queues_initialized:
            raise RuntimeError("Queues accessed before initialization")
        return self.tool_result_messages

    def set_agent_orchestrator(self, agent_orchestrator: 'BaseAgentOrchestrator'):
        self.agent_orchestrator = agent_orchestrator
        if not any(isinstance(tool, SendMessageTo) for tool in self.tools):
            self.tools.append(SendMessageTo(agent_orchestrator))
        logger.info(f"Agent orchestrator set for agent {self.role}")

    async def receive_agent_message(self, message: Message):
        logger.info(f"Agent {self.agent_id} received message from {message.sender_agent_id}")
        if not self._queues_initialized:
            logger.warning(f"Agent {self.agent_id} received message before queues were initialized. Initializing now.")
            self._initialize_queues()
        await self.incoming_agent_messages.put(message)
        if self.status != AgentStatus.RUNNING:
            self.start()

    async def handle_agent_messages(self):
        logger.info(f"Agent {self.role} started handling incoming messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                message = await asyncio.wait_for(self.get_incoming_agent_messages().get(), timeout=1.0)
                logger.info(f"Agent {self.role} processing message from {message.sender_agent_id}")
                llm_response = await self.conversation.send_user_message(f"Message from sender_agent_id:{message.sender_agent_id}, content:{message.content}")                
                await self.process_llm_response(llm_response)
            except asyncio.TimeoutError:
                pass

    def start(self):
        if self.status != AgentStatus.RUNNING:
            logger.info(f"Starting agent {self.role}")
            self._run_task = asyncio.create_task(self.run())

    async def run(self):
        try:
            logger.info(f"Agent {self.role} entering running state")
            self.status = AgentStatus.RUNNING
            # Initialize queues if not already done
            self._initialize_task_completed()
            self._initialize_queues()            
            await self.initialize_llm_conversation()
            
            agent_message_handler = asyncio.create_task(self.handle_agent_messages())
            tool_result_handler = asyncio.create_task(self.handle_tool_result_messages())

            done, pending = await asyncio.wait(
                [agent_message_handler, tool_result_handler, self.task_completed.wait()],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            await asyncio.gather(*pending, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error in agent {self.role} execution: {str(e)}")
            self.status = AgentStatus.ERROR
        else:
            logger.info(f"Agent {self.role} finished execution")
            self.status = AgentStatus.ENDED
        finally:
            await self.cleanup()

    async def initialize_llm_conversation(self):
        logger.info(f"Initializing LLM conversation for agent {self.role}")
        conversation_name = self._sanitize_conversation_name(self.role)
        self.conversation = await self.conversation_manager.start_conversation(
            conversation_name=conversation_name,
            llm=self.llm,
            persistence_provider_class=self.persistence_provider_class
        )

        initial_prompt = self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section()).build()
        logger.debug(f"Initial prompt for agent {self.role}: {initial_prompt}")
        initial_llm_response = await self.conversation.send_user_message(initial_prompt)
        await self.process_llm_response(initial_llm_response)

    async def handle_tool_result_messages(self):
        if not self._queues_initialized:
            logger.error(f"Agent {self.role} attempted to handle tool results before run() was called")
            return

        logger.info(f"Agent {self.role} started handling tool result messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                tool_result = await asyncio.wait_for(self.tool_result_messages.get(), timeout=1.0)
                logger.info(f"Agent {self.role} processing tool result: {tool_result}")
                llm_response = await self.conversation.send_user_message(f"Tool execution result: {tool_result}")
                await self.process_llm_response(llm_response)
            except asyncio.TimeoutError:
                pass
            
    async def process_llm_response(self, llm_response):
        logger.info(f"Agent {self.role} processing LLM response")
        tool_invocation = self.response_parser.parse_response(llm_response)

        if tool_invocation.is_valid():
            await self.execute_tool(tool_invocation)
        else:
            logger.info(f"LLM Response for agent {self.role}: {llm_response}")

    async def execute_tool(self, tool_invocation):
        tool_name = tool_invocation.name
        tool_arguments = tool_invocation.arguments

        logger.info(f"Agent {self.role} attempting to execute tool: {tool_name}")
        tool = next((t for t in self.tools if t.__class__.__name__ == tool_name), None)
        if tool:
            try:
                tool_result = await tool.execute(**tool_arguments)
                logger.info(f"Tool '{tool_name}' executed successfully by agent {self.role}. Result: {tool_result}")
                
                if not isinstance(tool, SendMessageTo):
                    await self.tool_result_messages.put(tool_result)
                else:
                    logger.info(f"SendMessageTo tool executed by agent {self.role}: {tool_result}")
            except Exception as e:
                error_message = f"Error executing tool '{tool_name}' by agent {self.role}: {str(e)}"
                logger.error(error_message)
                if not isinstance(tool, SendMessageTo):
                    await self.tool_result_messages.put(error_message)
        else:
            logger.warning(f"Tool '{tool_name}' not found for agent {self.role}.")

    def get_description(self):
        return f"A {self.role} agent with capabilities: {', '.join([tool.__class__.__name__ for tool in self.tools])}"

    def get_status(self):
        return self.status

    async def cleanup(self):
        """Perform cleanup operations, including clearing queues."""
        await super().cleanup()  # Call the superclass's cleanup method first

        # Clear the queues
        while not self.incoming_agent_messages.empty():
            self.incoming_agent_messages.get_nowait()
        while not self.tool_result_messages.empty():
            self.tool_result_messages.get_nowait()

        logger.info(f"Cleanup completed for agent: {self.role}")