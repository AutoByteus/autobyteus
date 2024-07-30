# File: autobyteus/agent/agent.py

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
    """

    def __init__(self, role: str, prompt_builder: PromptBuilder, llm: BaseLLM, tools: List[BaseTool],
                 use_xml_parser=True, persistence_provider_class: Optional[Type[PersistenceProvider]] = FileBasedPersistenceProvider):
        super().__init__()
        self.role = role
        self.prompt_builder = prompt_builder
        self.llm = llm
        self.tools = tools
        self.conversation_manager = ConversationManager()
        self.response_parser = XMLLLMResponseParser() if use_xml_parser else LLMResponseParser()
        self.persistence_provider_class = persistence_provider_class
        self.conversation = None
        self.task_completed = asyncio.Event()
        
        # Automatically register for task completion event
        self.register_task_completion_listener()


    async def run(self):
        """
        The main execution loop for the agent.
        
        This method initializes the conversation, sends the initial prompt to the LLM,
        and then enters a loop where it processes responses from the LLM and executes
        tools as needed. The loop continues until the task_completed event is set.
        """
        try:
            conversation_name = self._sanitize_conversation_name(self.role)
            self.conversation = await self.conversation_manager.start_conversation(
                conversation_name=conversation_name,
                llm=self.llm,
                persistence_provider_class=self.persistence_provider_class
            )

            # Build the prompt using the PromptBuilder
            prompt = self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section()).build()

            response = await self.conversation.send_user_message(prompt)

            while not self.task_completed.is_set():
                tool_invocation = self.response_parser.parse_response(response)

                if tool_invocation.is_valid():
                    name = tool_invocation.name
                    arguments = tool_invocation.arguments

                    tool = next((t for t in self.tools if t.__class__.__name__ == name), None)
                    if tool:
                        try:
                            result = await tool.execute(**arguments)
                            logger.info(f"Tool '{name}' result: {result}")
                            response = await self.conversation.send_user_message(result)
                        except Exception as e:
                            error_message = str(e)
                            logger.error(f"Tool '{name}' error: {error_message}")
                            response = await self.conversation.send_user_message(error_message)
                    else:
                        logger.warning(f"Tool '{name}' not found.")
                        break
                else:
                    logger.info(f"Assistant: {response}")
                    await asyncio.sleep(1)  # Prevent busy-waiting
            
            logger.info("Agent finished")
        finally:
            # Ensure cleanup is performed
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

    def on_task_completed(self, event_type: EventType, *args, **kwargs):
        """Event handler for task completion."""
        if event_type == EventType.TASK_COMPLETED:
            self.task_completed.set()

    def register_task_completion_listener(self):
        """Register a listener for the task completion event."""
        self.subscribe(EventType.TASK_COMPLETED, self.on_task_completed)

    async def cleanup(self):
        """Perform cleanup operations."""
        logger.info(f"Cleaning up resources for agent: {self.role}")
        if self.llm:
            await self.llm.close()