import asyncio
import logging
from typing import List, Optional
from autobyteus.agent.agent_instance import AgentInstance
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType
from autobyteus.agent.status import AgentStatus
from autobyteus.conversation.user_message import UserMessage
from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)

class AgentRuntime(EventEmitter):
    """
    Runtime engine for executing an AgentInstance.
    
    This class handles event processing, message queuing, and execution flow
    for a given agent configuration (AgentInstance).
    """
    
    def __init__(self, agent_instance: AgentInstance):
        super().__init__()
        self.instance = agent_instance
        self.status = AgentStatus.NOT_STARTED
        self._run_task = None
        self._queues_initialized = False
        self.task_completed = None
        
        # Subscribe to tool invocation events from all parsers
        for parser in self.instance.response_parsers:
            parser.subscribe(self, EventType.TOOL_INVOCATION, self.handle_tool_invocation_event)
            
        logger.info(f"Agent runtime initialized for role: {self.instance.role}, id: {self.instance.agent_id}")

    def _initialize_queues(self):
        if not self._queues_initialized:
            self.tool_result_messages = asyncio.Queue()
            self.user_messages = asyncio.Queue()
            self.pending_tool_invocations = asyncio.Queue()
            self._queues_initialized = True
            logger.info(f"Queues initialized for agent {self.instance.role}")

    def _initialize_task_completed(self):
        if self.task_completed is None:
            self.task_completed = asyncio.Event()
            logger.info(f"task_completed Event initialized for agent {self.instance.role}")

    def get_task_completed(self):
        if self.task_completed is None:
            raise RuntimeError("task_completed Event accessed before initialization")
        return self.task_completed

    async def run(self):
        try:
            logger.info(f"Starting execution for agent: {self.instance.role}")
            self._initialize_queues()
            self._initialize_task_completed()

            user_message_handler = asyncio.create_task(self.handle_user_messages())
            tool_result_handler = asyncio.create_task(self.handle_tool_result_messages())
            tool_invocation_handler = asyncio.create_task(self.handle_tool_invocation_queue())

            # Once everything is ready, set the status to RUNNING
            self.status = AgentStatus.RUNNING

            await asyncio.gather(user_message_handler, tool_result_handler, tool_invocation_handler)

        except Exception as e:
            logger.error(f"Error in agent {self.instance.role} execution: {str(e)}")
            self.status = AgentStatus.ERROR
        finally:
            self.status = AgentStatus.ENDED
            await self.cleanup()

    async def handle_user_messages(self):
        logger.info(f"Agent {self.instance.role} started handling user messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                user_message: UserMessage = await asyncio.wait_for(self.user_messages.get(), timeout=1.0)
                logger.info(f"Agent {self.instance.role} handling user message")
                response = await self.instance.llm.send_user_message(user_message)
                await self.process_llm_response(response)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"User message handler for agent {self.instance.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling user message for agent {self.instance.role}: {str(e)}")

    async def receive_user_message(self, message: UserMessage):
        """
        This method gracefully waits for the agent to become RUNNING
        if it's in the process of starting up, ensuring the queues are
        initialized before we put a message into them.
        """
        logger.info(f"Agent {self.instance.agent_id} received user message")

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
        logger.info(f"Agent {self.instance.role} started handling tool result messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                message = await asyncio.wait_for(self.tool_result_messages.get(), timeout=1.0)
                logger.info(f"Agent {self.instance.role} handling tool result message: {message}")
                tool_result_message = UserMessage(content=f"Tool execution result: {message}")
                response = await self.instance.llm.send_user_message(tool_result_message)
                await self.process_llm_response(response)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"Tool result handler for agent {self.instance.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling tool result for agent {self.instance.role}: {str(e)}")

    async def handle_tool_invocation_queue(self):
        """Handle pending tool invocations from the queue."""
        logger.info(f"Agent {self.instance.role} started handling tool invocations")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                tool_invocation: ToolInvocation = await asyncio.wait_for(
                    self.pending_tool_invocations.get(), timeout=1.0
                )
                logger.info(f"Agent {self.instance.role} handling tool invocation: {tool_invocation.name}")
                await self.execute_tool(tool_invocation)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"Tool invocation handler for agent {self.instance.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling tool invocation for agent {self.instance.role}: {str(e)}")

    async def process_llm_response(self, response: str) -> None:
        self.emit(EventType.ASSISTANT_RESPONSE, response=response)
        
        # Run all response parsers on the response
        for parser in self.instance.response_parsers:
            await parser.parse_response(response)
        
        # If no parsers or none found commands, log the response
        if not self.instance.response_parsers:
            logger.info(f"Assistant response for agent {self.instance.role}: {response}")

    def handle_tool_invocation_event(self, tool_invocation: ToolInvocation, **kwargs):
        """Handle tool invocation events from the response parsers."""
        if self.status != AgentStatus.RUNNING:
            logger.warning(f"Received tool invocation event while agent {self.instance.role} is not running")
            return
        
        logger.info(f"Agent {self.instance.role} received tool invocation event for {tool_invocation.name}")
        # Put the tool invocation in the queue for processing
        asyncio.create_task(self.pending_tool_invocations.put(tool_invocation))

    async def execute_tool(self, tool_invocation):
        name = tool_invocation.name
        arguments = tool_invocation.arguments
        logger.info(f"Agent {self.instance.role} attempting to execute tool: {name}")

        tool = next((t for t in self.instance.tools if t.get_name() == name), None)
        if tool:
            try:
                result = await tool.execute(**arguments)
                logger.info(f"Tool '{name}' executed successfully by agent {self.instance.role}. Result: {result}")
                await self.tool_result_messages.put(result)
            except Exception as e:
                error_message = str(e)
                logger.error(f"Error executing tool '{name}' by agent {self.instance.role}: {error_message}")
                await self.tool_result_messages.put(f"Error: {error_message}")
        else:
            logger.warning(f"Tool '{name}' not found for agent {self.instance.role}.")

    def start(self):
        """
        Starts the agent by creating a task that runs the main loop (run).
        Sets the AgentStatus to STARTING to prevent message enqueuing before
        the system is fully initialized.
        """
        if self.status in [AgentStatus.NOT_STARTED, AgentStatus.ENDED]:
            logger.info(f"Starting agent {self.instance.role}")
            self.status = AgentStatus.STARTING
            self._run_task = asyncio.create_task(self.run())
        elif self.status == AgentStatus.STARTING:
            logger.info(f"Agent {self.instance.role} is already in STARTING state.")
        elif self.status == AgentStatus.RUNNING:
            logger.info(f"Agent {self.instance.role} is already running.")
        else:
            logger.warning(f"Agent {self.instance.role} is in an unexpected state: {self.status}")

    def stop(self):
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()

    async def cleanup(self):
        while not self.tool_result_messages.empty():
            self.tool_result_messages.get_nowait()
        while not self.user_messages.empty():
            self.user_messages.get_nowait()
        while not self.pending_tool_invocations.empty():
            self.pending_tool_invocations.get_nowait()
        await self.instance.llm.cleanup()
        logger.info(f"Cleanup completed for agent: {self.instance.role}")

    def on_task_completed(self, *args, **kwargs):
        logger.info(f"Task completed event received for agent: {self.instance.role}")
        self.task_completed.set()
