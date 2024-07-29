# File: autobyteus/agent/group/coordinator_agent.py

import os
import logging
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.llm.base_llm import BaseLLM
from typing import List
from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class CoordinatorAgent(GroupAwareAgent):
    def __init__(self, role: str, llm: BaseLLM, tools: List[BaseTool]):
        prompt_builder = PromptBuilder.from_file(self._get_prompt_template_path())
        super().__init__(role, prompt_builder, llm, tools)

    def _get_prompt_template_path(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, 'coordinator_agent.prompt')

    def generate_dynamic_prompt(self):
        agent_descriptions = "\n".join([f"- {agent.role}: {agent.get_description()}" for agent in self.agent_group.agents.values() if agent != self])
        self.prompt_builder.set_variable_value("agent_descriptions", agent_descriptions)
        self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section())

    async def run(self, user_task: str):
        conversation_name = self._sanitize_conversation_name(self.role)
        conversation = await self.conversation_manager.start_conversation(
            conversation_name=conversation_name,
            llm=self.llm,
            persistence_provider_class=self.persistence_provider_class
        )

        self.generate_dynamic_prompt()
        prompt = self.prompt_builder.build()
        
        response = await conversation.send_user_message(f"{prompt}\n\nUser task: {user_task}")
        
        while True:
            tool_invocation = self.response_parser.parse_response(response)

            if tool_invocation.is_valid():
                name = tool_invocation.name
                arguments = tool_invocation.arguments

                tool = next((t for t in self.tools if t.__class__.__name__ == name), None)
                if tool:
                    try:
                        result = await tool.execute(**arguments)
                        logger.info(f"Tool '{name}' result: {result}")
                        response = await conversation.send_user_message(result)
                    except Exception as e:
                        error_message = str(e)
                        logger.error(f"Tool '{name}' error: {error_message}")
                        response = await conversation.send_user_message(error_message)
                else:
                    logger.warning(f"Tool '{name}' not found.")
                    break
            else:
                logger.info(f"Assistant: {response}")
                return response