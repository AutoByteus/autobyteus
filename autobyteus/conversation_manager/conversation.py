from typing import Union

from autobyteus.llm.base_llm import BaseLLM

class Conversation:
    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self.history = []
    
    async def start(self):
        await self.llm.initialize()
    
    async def send_user_message(self, user_input: str) -> str:
        user_message_index = len(self.history) + 1
        response = await self.llm.send_user_message(user_input, user_message_index=user_message_index)
        self.history.append(("user", user_input))
        self.history.append(("assistant", response))
        return response