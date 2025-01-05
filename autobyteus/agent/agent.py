import asyncio
import logging
from typing import List, Optional
from autobyteus.agent.response_parser.tool_usage_command_parser import ToolUsageCommandParser
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.events.event_types import EventType
from autobyteus.agent.status import AgentStatus
from autobyteus.conversation.user_message import UserMessage
from autobyteus.conversation.conversation import Conversation

logger = logging.getLogger(__name__)

class Agent(EventEmitter):
    def __init__(self, role: str, llm: BaseLLM, tools: Optional[List[BaseTool]] = None,
                 agent_id=None,
                 prompt_builder: Optional[PromptBuilder] = None,
                 initial_user_message: Optional[UserMessage] = None):
        super().__init__()
        self.role = role
        self.llm = llm
        self.tools = tools or []
        self.tool_usage_response_parser = ToolUsageCommandParser() if self.tools else None
        self.conversation = None
        self.agent_id = agent_id or f"{self.role}-001"
        self.status = AgentStatus.NOT_STARTED
        self._run_task = None
        self._queues_initialized = False
        self.task_completed = None
        self.prompt_builder = prompt_builder
        self.initial_user_message = initial_user_message

        if not self.prompt_builder and not self.initial_user_message:
            raise ValueError("Either prompt_builder or initial_user_message must be provided")

        if self.tools:
            self.set_agent_id_on_tools()
            
        logger.info(f"StandaloneAgent initialized with role: {self.role}, agent_id: {self.agent_id}")

    def _initialize_queues(self):
        if not self._queues_initialized:
            self.tool_result_messages = asyncio.Queue()
            self.user_messages = asyncio.Queue()
            self._queues_initialized = True
            logger.info(f"Queues initialized for agent {self.role}")

    def _initialize_task_completed(self):
        if self.task_completed is None:
            self.task_completed = asyncio.Event()
            logger.info(f"task_completed Event initialized for agent {self.role}")

    def get_task_completed(self):
        if self.task_completed is None:
            raise RuntimeError("task_completed Event accessed before initialization")
        return self.task_completed

    async def run(self):
        try:
            logger.info(f"Starting execution for agent: {self.role}")
            self._initialize_queues()
            self._initialize_task_completed()
            await self.initialize_conversation()

            user_message_handler = asyncio.create_task(self.handle_user_messages())
            tool_result_handler = asyncio.create_task(self.handle_tool_result_messages())

            # Once everything is ready, set the status to RUNNING
            self.status = AgentStatus.RUNNING

            await asyncio.gather(user_message_handler, tool_result_handler)

        except Exception as e:
            logger.error(f"Error in agent {self.role} execution: {str(e)}")
            self.status = AgentStatus.ERROR
        finally:
            self.status = AgentStatus.ENDED
            await self.cleanup()

    async def handle_user_messages(self):
        logger.info(f"Agent {self.role} started handling user messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                user_message: UserMessage = await asyncio.wait_for(self.user_messages.get(), timeout=1.0)
                logger.info(f"Agent {self.role} handling user message")
                response = await self.conversation.send_user_message(user_message.content, user_message.file_paths)
                await self.process_llm_response(response)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"User message handler for agent {self.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling user message for agent {self.role}: {str(e)}")

    async def receive_user_message(self, message: UserMessage):
        """
        This method gracefully waits for the agent to become RUNNING
        if it's in the process of starting up, ensuring the queues are
        initialized before we put a message into them.
        """
        logger.info(f"Agent {self.agent_id} received user message")

        # If the agent is not started (or ended), begin the start process
        if self.status in [AgentStatus.NOT_STARTED, AgentStatus.ENDED]:
            self.start()

        # If the agent is still starting, wait until it transitions to RUNNING
        while self.status == AgentStatus.STARTING:
            await asyncio.sleep(0.1)

        if self.status != AgentStatus.RUNNING:
            logger.error(f"Agent is not in a running state: {self.status}")
            return

        # Now that we are running, safely place the message in the queue
        await self.user_messages.put(message)

    async def handle_tool_result_messages(self):
        logger.info(f"Agent {self.role} started handling tool result messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                message = await asyncio.wait_for(self.tool_result_messages.get(), timeout=1.0)
                logger.info(f"Agent {self.role} handling tool result message: {message}")
                response = await self.conversation.send_user_message(f"Tool execution result: {message}")
                await self.process_llm_response(response)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"Tool result handler for agent {self.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling tool result for agent {self.role}: {str(e)}")

    async def initialize_conversation(self):
        logger.info(f"Initializing conversation for agent: {self.role}")
        self.conversation = Conversation(self.llm)

        if self.initial_user_message:
            initial_message = self.initial_user_message
        else:
            prompt_content = self.prompt_builder.set_variable_value(
                "external_tools", 
                self._get_external_tools_section()
            ).build()
            initial_message = UserMessage(content=prompt_content)

        logger.debug(f"Initial user message for agent {self.role}: {initial_message}")
        initial_llm_response = await self.conversation.send_user_message(
            initial_message.content,
            initial_message.file_paths
        )
        await self.process_llm_response(initial_llm_response)

    async def process_llm_response(self, response: str) -> None:
        self.emit(EventType.ASSISTANT_RESPONSE, response=response)
        
        if self.tools and self.tool_usage_response_parser:
            tool_invocation = self.tool_usage_response_parser.parse_response(response)
            if tool_invocation.is_valid():
                await self.execute_tool(tool_invocation)
                return

        logger.info(f"Assistant response for agent {self.role}: {response}")

    async def execute_tool(self, tool_invocation):
        name = tool_invocation.name
        arguments = tool_invocation.arguments
        logger.info(f"Agent {self.role} attempting to execute tool: {name}")

        tool = next((t for t in self.tools if t.get_name() == name), None)
        if tool:
            try:
                result = await tool.execute(**arguments)
                logger.info(f"Tool '{name}' executed successfully by agent {self.role}. Result: {result}")
                await self.tool_result_messages.put(result)
            except Exception as e:
                error_message = str(e)
                logger.error(f"Error executing tool '{name}' by agent {self.role}: {error_message}")
                await self.tool_result_messages.put(f"Error: {error_message}")
        else:
            logger.warning(f"Tool '{name}' not found for agent {self.role}.")

    def start(self):
        """
        Starts the agent by creating a task that runs the main loop (run).
        Sets the AgentStatus to STARTING to prevent message enqueuing before
        the system is fully initialized.
        """
        if self.status in [AgentStatus.NOT_STARTED, AgentStatus.ENDED]:
            logger.info(f"Starting agent {self.role}")
            self.status = AgentStatus.STARTING
            self._run_task = asyncio.create_task(self.run())
        elif self.status == AgentStatus.STARTING:
            logger.info(f"Agent {self.role} is already in STARTING state.")
        elif self.status == AgentStatus.RUNNING:
            logger.info(f"Agent {self.role} is already running.")
        else:
            logger.warning(f"Agent {self.role} is in an unexpected state: {self.status}")

    def stop(self):
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()

    async def cleanup(self):
        while not self.tool_result_messages.empty():
            self.tool_result_messages.get_nowait()
        while not self.user_messages.empty():
            self.user_messages.get_nowait()
        await self.llm.cleanup()
        logger.info(f"Cleanup completed for agent: {self.role}")

    def set_agent_id_on_tools(self):
        if self.tools:
            for tool in self.tools:
                tool.set_agent_id(self.agent_id)

    def _get_external_tools_section(self) -> str:
        if not self.tools:
            return ""
            
        external_tools_section = ""
        for i, tool in enumerate(self.tools):
            external_tools_section += f"  {i + 1} {tool.tool_usage_xml()}\n\n"
        return external_tools_section.strip()

    def on_task_completed(self, *args, **kwargs):
        logger.info(f"Task completed event received for agent: {self.role}")
        self.task_completed.set()
