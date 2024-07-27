
from typing import List, Type, Optional
from autobyteus.conversation.conversation_manager import ConversationManager
from autobyteus.conversation.persistence.file_based_persistence_provider import FileBasedPersistenceProvider
from autobyteus.conversation.persistence.provider import PersistenceProvider
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.llm_response_parser import LLMResponseParser
from autobyteus.agent.xml_llm_response_parser import XMLLLMResponseParser
from autobyteus.prompt.prompt_builder import PromptBuilder

class Agent(EventEmitter):
    def __init__(self, role: str, prompt_builder: PromptBuilder, llm: BaseLLM, tools: List[BaseTool],
                 use_xml_parser=True, persistence_provider_class: Optional[Type[PersistenceProvider]] = FileBasedPersistenceProvider):
        self.role = role
        self.prompt_builder = prompt_builder
        self.llm = llm
        self.tools = tools
        self.conversation_manager = ConversationManager()
        self.response_parser = XMLLLMResponseParser() if use_xml_parser else LLMResponseParser()
        self.persistence_provider_class = persistence_provider_class

    async def run(self):
        conversation_name = self._sanitize_conversation_name(self.role)
        conversation = await self.conversation_manager.start_conversation(
            conversation_name=conversation_name,
            llm=self.llm,
            persistence_provider_class=self.persistence_provider_class
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
                    try:
                        result = await tool.execute(**arguments)
                        print(f"Tool '{name}' result: {result}")
                        response = await conversation.send_user_message(result)
                    except Exception as e:
                        error_message = str(e)
                        print(f"Tool '{name}' error: {error_message}")
                        response = await conversation.send_user_message(error_message)
                else:
                    print(f"Tool '{name}' not found.")
                    break
            else:
                print(f"Assistant: {response}")
                break

    def _get_external_tools_section(self):
        external_tools_section = ""
        for i, tool in enumerate(self.tools):
            external_tools_section += f"  {i + 1} {tool.tool_usage_xml()}\n\n"
        return external_tools_section.strip()

    @staticmethod
    def _sanitize_conversation_name(name: str) -> str:
        return ''.join(c if c.isalnum() else '_' for c in name)
    

    