# File: autobyteus/agent/agent.py

import asyncio
import logging
from typing import List, Type, Optional
import uuid
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

logger = logging.getLogger(__name__)

class StandaloneAgent(EventEmitter):
    """
    A standalone agent capable of interacting with an LLM and executing tools.
    
    This agent operates independently, without awareness of other agents. It processes
    tasks sequentially, interacting with its assigned LLM and executing tools as needed.
    
    Attributes:
        role (str): The role or identifier of the agent.
        prompt_builder (PromptBuilder): Used to construct prompts for the LLM.
        llm (BaseLLM): The language model the agent interacts with.
        tools (List[BaseTool]): The tools available to the agent.
        conversation_manager (ConversationManager): Manages the agent's conversations.
        response_parser (XMLLLMResponseParser): Parses responses from the LLM.
        persistence_provider_class (Type[PersistenceProvider]): Class for persisting conversations.
        conversation: The current conversation instance.
        task_completed (asyncio.Event): Event to signal task completion.
        agent_id (str): The unique identifier for the agent. If not provided, it's generated as "{role}_001".

    Args:
        role (str): The role or identifier of the agent.
        prompt_builder (PromptBuilder): Used to construct prompts for the LLM.
        llm (BaseLLM): The language model the agent interacts with.
        tools (List[BaseTool]): The tools available to the agent.
        use_xml_parser (bool, optional): Whether to use XML parser for LLM responses. Defaults to True.
        persistence_provider_class (Type[PersistenceProvider], optional): Class for persisting conversations. 
            Defaults to FileBasedPersistenceProvider.
        agent_id (str, optional): The unique identifier for the agent. If not provided, a default id is generated.
    """

    def __init__(self, role: str, prompt_builder: PromptBuilder, llm: BaseLLM, tools: List[BaseTool],
                 use_xml_parser=True, persistence_provider_class: Optional[Type[PersistenceProvider]] = FileBasedPersistenceProvider, agent_id=None):
        super().__init__()
        self.role = role
        self.prompt_builder = prompt_builder
        self.llm = llm
        self.tools = tools
        self.conversation_manager = ConversationManager()
        self.response_parser = XMLLLMResponseParser() if use_xml_parser else LLMResponseParser()
        self.persistence_provider_class = persistence_provider_class
        self.conversation = None
        self.task_completed = None

        # Generate default agent_id if not provided
        if agent_id is None:
            self.agent_id = f"{self.role}-001"
        else:
            self.agent_id = agent_id

        # Set agent_id on each tool
        self.set_agent_id_on_tools()
        self.register_task_completion_listener()
        logger.info(f"StandaloneAgent initialized with role: {self.role} and agent_id: {self.agent_id}")

    def _initialize_task_completed(self):
        if self.task_completed is None:
            self.task_completed = asyncio.Event()
            logger.info(f"task_completed Event initialized for agent {self.role}")

    def get_task_completed(self):
        if self.task_completed is None:
            raise RuntimeError("task_completed Event accessed before initialization")
        return self.task_completed

    def get_agent_id(self) -> str:
        """Get the unique identifier of the agent."""
        return self.agent_id

    def set_agent_id_on_tools(self):
            for tool in self.tools:
                tool.set_agent_id(self.agent_id)

    async def run(self):
        """
        The main execution loop for the agent.
        
        This method initializes the conversation, sends the initial prompt to the LLM,
        and then enters a loop where it processes responses from the LLM and executes
        tools as needed. The loop continues until the task_completed event is set.
        """
        try:
            logger.info(f"Starting execution for agent: {self.role}")
            self._initialize_task_completed()
            conversation_name = self._sanitize_conversation_name(self.role)
            self.conversation = await self.conversation_manager.start_conversation(
                conversation_name=conversation_name,
                llm=self.llm,
                persistence_provider_class=self.persistence_provider_class
            )
            logger.info(f"Conversation started for agent: {self.role}")

            prompt = self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section()).build()
            logger.debug(f"Initial prompt for agent {self.role}: {prompt}")

            response = await self.conversation.send_user_message(prompt)
            logger.info(f"Received initial LLM response for agent {self.role}")

            while not self.task_completed.is_set():
                tool_invocation = self.response_parser.parse_response(response)

                if tool_invocation.is_valid():
                    name = tool_invocation.name
                    arguments = tool_invocation.arguments
                    logger.info(f"Agent {self.role} attempting to execute tool: {name}")

                    tool = next((t for t in self.tools if t.get_name() == name), None)
                    if tool:
                        try:
                            result = await tool.execute(**arguments)
                            logger.info(f"Tool '{name}' executed successfully by agent {self.role}. Result: {result}")
                            response = await self.conversation.send_user_message(result)
                        except Exception as e:
                            error_message = str(e)
                            logger.error(f"Error executing tool '{name}' by agent {self.role}: {error_message}")
                            response = await self.conversation.send_user_message(error_message)
                    else:
                        logger.warning(f"Tool '{name}' not found for agent {self.role}.")
                        break
                else:
                    logger.info(f"Assistant response for agent {self.role}: {response}")
                    await asyncio.sleep(1)
            
            logger.info(f"Agent {self.role} finished execution")
        finally:
            await self.cleanup()

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

    async def cleanup(self):
        """Perform cleanup operations."""
        logger.info(f"Cleaning up resources for agent: {self.role}")
        if self.llm:
            await self.llm.cleanup()
        self.task_completed.clear()  # Reset the task_completed event
        logger.info(f"Cleanup completed for agent: {self.role}")

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