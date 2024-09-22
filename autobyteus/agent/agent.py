import asyncio
import logging
from typing import List, Type, Optional
from autobyteus.agent.llm_response_parser import LLMResponseParser
from autobyteus.conversation.conversation_manager import ConversationManager
from autobyteus.conversation.persistence.file_based_persistence_provider import FileBasedPersistenceProvider
from autobyteus.conversation.persistence.provider import PersistenceProvider
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.xml_llm_response_parser import XMLLLMResponseParser
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.events.event_types import EventType
from autobyteus.agent.status import AgentStatus

logger = logging.getLogger(__name__)

class StandaloneAgent(EventEmitter):
    def __init__(self, role: str, llm: BaseLLM, tools: List[BaseTool],
                 use_xml_parser=True, 
                 persistence_provider_class: Optional[Type[PersistenceProvider]] = FileBasedPersistenceProvider, 
                 agent_id=None,
                 prompt_builder: Optional[PromptBuilder] = None,
                 initial_prompt: Optional[str] = None):
        super().__init__()
        self.role = role
        self.llm = llm
        self.tools = tools
        self.conversation_manager = ConversationManager()
        self.response_parser = XMLLLMResponseParser() if use_xml_parser else LLMResponseParser()
        self.persistence_provider_class = persistence_provider_class
        self.conversation = None
        self.agent_id = agent_id or f"{self.role}-001"
        self.status = AgentStatus.NOT_STARTED
        self._run_task = None
        self._queues_initialized = False
        self.task_completed = None
        self.prompt_builder = prompt_builder
        self.initial_prompt = initial_prompt

        if not self.prompt_builder and not self.initial_prompt:
            raise ValueError("Either prompt_builder or initial_prompt must be provided")

        self.set_agent_id_on_tools()
        self.register_task_completion_listener()
        logger.info(f"StandaloneAgent initialized with role: {self.role} and agent_id: {self.agent_id}")


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
            await self.initialize_llm_conversation()
            
            self.status = AgentStatus.RUNNING
            
            user_message_handler = asyncio.create_task(self.handle_user_messages())
            tool_result_handler = asyncio.create_task(self.handle_tool_result_messages())
            
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
                message = await asyncio.wait_for(self.user_messages.get(), timeout=1.0)
                logger.info(f"Agent {self.role} handling user message")
                response = await self.conversation.send_user_message(message)
                await self.process_llm_response(response)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"User message handler for agent {self.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling user message for agent {self.role}: {str(e)}")

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

    async def initialize_llm_conversation(self):
        logger.info(f"Initializing LLM conversation for agent {self.role}")
        conversation_name = self._sanitize_conversation_name(self.role)
        self.conversation = await self.conversation_manager.start_conversation(
            conversation_name=conversation_name,
            llm=self.llm,
            persistence_provider_class=self.persistence_provider_class
        )

        if self.initial_prompt:
            initial_prompt = self.initial_prompt
        else:
            initial_prompt = self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section()).build()

        logger.debug(f"Initial prompt for agent {self.role}: {initial_prompt}")
        initial_llm_response = await self.conversation.send_user_message(initial_prompt)
        await self.process_llm_response(initial_llm_response)

    async def process_llm_response(self, response):
        self.emit(EventType.ASSISTANT_RESPONSE, agent_id=self.agent_id, response=response)
        tool_invocation = self.response_parser.parse_response(response)
        if tool_invocation.is_valid():
            await self.execute_tool(tool_invocation)
        else:
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

    async def receive_user_message(self, message: str):
        logger.info(f"Agent {self.agent_id} received user message")
        await self.user_messages.put(message)
        if self.status != AgentStatus.RUNNING:
            self.start()

    def start(self):
        if self.status == AgentStatus.NOT_STARTED or self.status == AgentStatus.ENDED:
            logger.info(f"Starting agent {self.role}")
            self._run_task = asyncio.create_task(self.run())

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
        for tool in self.tools:
            tool.set_agent_id(self.agent_id)

    def _get_external_tools_section(self):
        """Generate a string representation of all available tools."""
        external_tools_section = ""
        for i, tool in enumerate(self.tools):
            external_tools_section += f"  {i + 1} {tool.tool_usage_xml()}\n\n"
        return external_tools_section.strip()

    @staticmethod
    def _sanitize_conversation_name(name: str) -> str:
        """Sanitize the conversation name to ensure it's valid for storage."""
        return ''.join(c if c.isalnum() else '_' for c in name)

    def on_task_completed(self, *args, **kwargs):
        """Event handler for task completion."""
        #event_type = kwargs.get('event_type')
        #agent_id = kwargs.get('agent_id')
        
        #if event_type == EventType.TASK_COMPLETED and agent_id == self.agent_id:
        logger.info(f"Task completed event received for agent: {self.role}")
        self.task_completed.set()

    def register_task_completion_listener(self):
        """Register a listener for the task completion event."""
        logger.info(f"Registering task completion listener for agent: {self.role}")
        self.subscribe(EventType.TASK_COMPLETED, self.on_task_completed, self.agent_id)