# File: autobyteus/agent/group/coordinator_agent.py

import os
import logging
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent, AgentStatus
from autobyteus.events.event_types import EventType
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.llm.base_llm import BaseLLM
from typing import List
from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class CoordinatorAgent(GroupAwareAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_dynamic_prompt(self):
        agent_descriptions = "\n".join([f"- {agent.role}: {agent.get_description()}" for agent in self.agent_group.agents.values() if agent != self])
        self.prompt_builder.set_variable_value("agent_descriptions", agent_descriptions)
        self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section())

    async def process_llm_response(self, llm_response):
        tool_invocation = self.response_parser.parse_response(llm_response)

        if tool_invocation.is_valid():
            await self.execute_tool(tool_invocation)
        else:
            logger.info(f"Coordinator Response: {llm_response}")
            # The coordinator has finished its task
            self.emit(EventType.TASK_COMPLETED)

    async def initialize_llm_conversation(self):
        conversation_name = self._sanitize_conversation_name(self.role)
        self.conversation = await self.conversation_manager.start_conversation(
            conversation_name=conversation_name,
            llm=self.llm,
            persistence_provider_class=self.persistence_provider_class
        )

        self.generate_dynamic_prompt()
        initial_prompt = self.prompt_builder.build()
        
        if self.user_task:
            initial_prompt += f"\n\nUser task: {self.user_task}"
        
        initial_llm_response = await self.conversation.send_user_message(initial_prompt)
        await self.process_llm_response(initial_llm_response)
