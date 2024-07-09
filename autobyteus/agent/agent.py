from typing import List
from autobyteus.conversation.conversation_manager import ConversationManager
from autobyteus.conversation.memory.in_memory_provider import InMemoryProvider
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.llm_response_parser import LLMResponseParser

class Agent:
    def __init__(self, role: str, prompt: str, llm: BaseLLM, tools: List[BaseTool]):
        self.role = role
        self.prompt = prompt
        self.llm = llm
        self.tools = tools
        self.conversation_manager = ConversationManager()
        self.response_parser = LLMResponseParser()

    async def run(self):
        conversation = await self.conversation_manager.start_conversation(
            conversation_name=self.role,
            llm=self.llm,
            memory_provider_class=InMemoryProvider
        )

        response = await conversation.send_user_message(self.prompt)

        while True:
            parsed_response = self.response_parser.parse_response(response)

            if parsed_response.is_tool_invocation():
                tool_name = parsed_response.tool_name
                tool_args = parsed_response.tool_args

                tool = next((t for t in self.tools if t.__class__.__name__ == tool_name), None)
                if tool:
                    result = await tool.execute(**tool_args)
                    print(f"Tool '{tool_name}' result: {result}")
                    response = await conversation.send_user_message(result)
                else:
                    print(f"Tool '{tool_name}' not found.")
                    break
            else:
                print(f"Assistant: {response}")
                break