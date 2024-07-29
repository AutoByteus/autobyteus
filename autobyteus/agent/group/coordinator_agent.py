# File: autobyteus/agent/group/coordinator_agent.py

import os
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.llm.base_llm import BaseLLM
from typing import List
from autobyteus.tools.base_tool import BaseTool

class CoordinatorAgent(GroupAwareAgent):
    def __init__(self, role: str, llm: BaseLLM, tools: List[BaseTool]):
        prompt_builder = PromptBuilder.from_template(self._get_prompt_template_path())
        super().__init__(role, prompt_builder, llm, tools)

    def _get_prompt_template_path(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, 'coordinator_agent.prompt')

    def generate_dynamic_prompt(self):
        agent_descriptions = "\n".join([f"- {agent.role}: {agent.get_description()}" for agent in self.agent_group.agents.values() if agent != self])
        self.prompt_builder.set_variable_value("agent_descriptions", agent_descriptions)

    async def initialize(self):
        self.generate_dynamic_prompt()
        await super().initialize()

    async def run(self, user_task: str):
        if not self.conversation:
            await self.initialize()

        response = await self.conversation.send_user_message(f"User task: {user_task}")
        
        while True:
            tool_invocation = self.response_parser.parse_response(response)

            if tool_invocation.is_valid():
                name = tool_invocation.name
                arguments = tool_invocation.arguments

                tool = next((t for t in self.tools if t.__class__.__name__ == name), None)
                if tool:
                    try:
                        result = await tool.execute(**arguments)
                        response = await self.conversation.send_user_message(result)
                    except Exception as e:
                        error_message = str(e)
                        response = await self.conversation.send_user_message(error_message)
                else:
                    break
            else:
                return response