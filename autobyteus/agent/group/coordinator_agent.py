# File: autobyteus/agent/group/coordinator_agent.py

import asyncio
import os
import logging
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent, AgentStatus
from autobyteus.agent.message.message_types import MessageType
from autobyteus.agent.message.message import Message

from autobyteus.events.event_types import EventType
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.llm.base_llm import BaseLLM
from typing import List
from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class CoordinatorAgent(GroupAwareAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info(f"CoordinatorAgent initialized with role: {self.role}")

    def generate_dynamic_prompt(self):
        """
        Generate a dynamic prompt for the CoordinatorAgent.
        """
        logger.info(f"Generating dynamic prompt for CoordinatorAgent {self.role}")
        agent_descriptions = "\n".join([f"- {agent.role}: {agent.get_description()}" for agent in self.agent_orchestrator.agents.values() if agent != self])
        self.prompt_builder.set_variable_value("agent_descriptions", agent_descriptions)
        self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section())
        logger.debug(f"Dynamic prompt generated for CoordinatorAgent {self.role}")

    async def process_llm_response(self, llm_response):
        """
        Process the LLM response for the CoordinatorAgent.
        """
        logger.info(f"CoordinatorAgent {self.role} processing LLM response")
        tool_invocation = self.response_parser.parse_response(llm_response)

        if tool_invocation.is_valid():
            await self.execute_tool(tool_invocation)
        else:
            logger.info(f"Coordinator Response for agent {self.role}: {llm_response}")
            logger.info(f"CoordinatorAgent {self.role} task completed, emitting TASK_COMPLETED event")
            self.emit(EventType.TASK_COMPLETED)
            
    async def initialize_llm_conversation(self):
        """
        Initialize the LLM conversation for the CoordinatorAgent.
        """
        logger.info(f"Initializing LLM conversation for CoordinatorAgent {self.role}")
        conversation_name = self._sanitize_conversation_name(self.role)
        self.conversation = await self.conversation_manager.start_conversation(
            conversation_name=conversation_name,
            llm=self.llm,
            persistence_provider_class=self.persistence_provider_class
        )

        self.generate_dynamic_prompt()
        initial_prompt = self.prompt_builder.build()
        logger.debug(f"Initial prompt for CoordinatorAgent {self.role}: {initial_prompt}")
        
        initial_llm_response = await self.conversation.send_user_message(initial_prompt)
        await self.process_llm_response(initial_llm_response)