from typing import List
from autobyteus.conversation.conversation_manager import ConversationManager
from autobyteus.conversation.memory.in_memory_provider import InMemoryProvider
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.llm_response_parser import LLMResponseParser
from autobyteus.agent.xml_llm_response_parser import XMLLLMResponseParser
from autobyteus.prompt.prompt_builder import PromptBuilder

class Agent:
    def __init__(self, role: str, prompt_builder: PromptBuilder, llm: BaseLLM, tools: List[BaseTool], use_xml_parser=True):
        self.role = role
        self.prompt_builder = prompt_builder
        self.llm = llm
        self.tools = tools
        self.conversation_manager = ConversationManager()
        self.response_parser = XMLLLMResponseParser() if use_xml_parser else LLMResponseParser()

    async def run(self):
        conversation = await self.conversation_manager.start_conversation(
            conversation_name=self.role,
            llm=self.llm,
            memory_provider_class=InMemoryProvider
        )

        # Build the prompt using the PromptBuilder
        prompt = self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section()).build()

        response = await conversation.send_user_message(prompt)

        while True:
            tool_invocation = self.response_parser.parse_response(response)

            if tool_invocation.is_valid():
                name = tool_invocation.name
                arguments = tool_invocation.arguments

                tool = next((t for t in self.tools if t.__class__.__name__ == name), None)
                if tool:
                    result = await tool.execute(**arguments)
                    print(f"Tool '{name}' result: {result}")
                    response = await conversation.send_user_message(result)
                else:
                    print(f"Tool '{name}' not found.")
                    break
            else:
                response = await conversation.send_user_message("continue please")
                print(f"Assistant: {response}")
                break

    def _get_external_tools_section(self):
        external_tools_section = ""
        for i, tool in enumerate(self.tools, start=1):
            external_tools_section += f"{i}. {tool.tool_usage_xml()}\n\n"
        return external_tools_section.strip()