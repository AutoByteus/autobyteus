# File: autobyteus/agent/group_aware_agent.py

import asyncio
from collections import deque
import logging
from enum import Enum
from autobyteus.agent.agent import StandaloneAgent
from autobyteus.agent.group.send_message_to import SendMessageTo
from autobyteus.events.event_types import EventType

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    ENDED = "ended"
    ERROR = "error"

class GroupAwareAgent(StandaloneAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_group = None
        self.incoming_agent_messages = asyncio.Queue()
        self.tool_result_messages = asyncio.Queue()
        self.status = AgentStatus.NOT_STARTED
        self._run_task = None

    def set_agent_group(self, agent_group):
        self.agent_group = agent_group
        if not any(isinstance(tool, SendMessageTo) for tool in self.tools):
            self.tools.append(SendMessageTo(agent_group))

    async def receive_agent_message(self, sender_role: str, message: str):
        await self.incoming_agent_messages.put((sender_role, message))
        if self.status == AgentStatus.NOT_STARTED:
            self.start()

    def start(self):
        if self.status == AgentStatus.NOT_STARTED:
            self._run_task = asyncio.create_task(self.run())

    async def run(self):
            try:
                self.status = AgentStatus.RUNNING
                await self.initialize_llm_conversation()
                
                agent_message_handler = asyncio.create_task(self.handle_agent_messages())
                tool_result_handler = asyncio.create_task(self.handle_tool_result_messages())

                # Wait for either the tasks to complete or the task_completed event to be set
                done, pending = await asyncio.wait(
                    [agent_message_handler, tool_result_handler, self.task_completed.wait()],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel any pending tasks
                for task in pending:
                    task.cancel()

                # Wait for the cancelled tasks to finish
                await asyncio.gather(*pending, return_exceptions=True)

            except Exception as e:
                logger.error(f"Error in agent execution: {str(e)}")
                self.status = AgentStatus.ERROR
            else:
                self.status = AgentStatus.ENDED
            finally:
                # Cleanup resources
                await self.cleanup()


    async def initialize_llm_conversation(self):
        conversation_name = self._sanitize_conversation_name(self.role)
        self.conversation = await self.conversation_manager.start_conversation(
            conversation_name=conversation_name,
            llm=self.llm,
            persistence_provider_class=self.persistence_provider_class
        )

        initial_prompt = self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section()).build()
        initial_llm_response = await self.conversation.send_user_message(initial_prompt)
        await self.process_llm_response(initial_llm_response)

    async def handle_agent_messages(self):
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                sender_role, message = await asyncio.wait_for(self.incoming_agent_messages.get(), timeout=1.0)
                llm_response = await self.conversation.send_user_message(f"Message from {sender_role}: {message}")
                await self.process_llm_response(llm_response)
            except asyncio.TimeoutError:
                pass

    async def handle_tool_result_messages(self):
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                tool_result = await asyncio.wait_for(self.tool_result_messages.get(), timeout=1.0)
                llm_response = await self.conversation.send_user_message(f"Tool execution result: {tool_result}")
                await self.process_llm_response(llm_response)
            except asyncio.TimeoutError:
                pass
            
    async def process_llm_response(self, llm_response):
        tool_invocation = self.response_parser.parse_response(llm_response)

        if tool_invocation.is_valid():
            await self.execute_tool(tool_invocation)
        else:
            logger.info(f"LLM Response: {llm_response}")

    async def execute_tool(self, tool_invocation):
            tool_name = tool_invocation.name
            tool_arguments = tool_invocation.arguments

            tool = next((t for t in self.tools if t.__class__.__name__ == tool_name), None)
            if tool:
                try:
                    tool_result = await tool.execute(**tool_arguments)
                    logger.info(f"Tool '{tool_name}' execution result: {tool_result}")
                    
                    # Check if the tool is SendMessageTo
                    if not isinstance(tool, SendMessageTo):
                        await self.tool_result_messages.put(tool_result)
                    else:
                        logger.info(f"SendMessageTo tool executed: {tool_result}")
                except Exception as e:
                    error_message = f"Error executing tool '{tool_name}': {str(e)}"
                    logger.error(error_message)
                    if not isinstance(tool, SendMessageTo):
                        await self.tool_result_messages.put(error_message)
            else:
                logger.warning(f"Tool '{tool_name}' not found in available tools.")

    def get_description(self):
        return f"A {self.role} agent with capabilities: {', '.join([tool.__class__.__name__ for tool in self.tools])}"

    def get_status(self):
        return self.status
