# claude_chat_api.py
import os
import anthropic
from typing import Optional, List

from autobyteus.llm.api.base_chat import BaseChatAPI, Message, MessageRole

class ClaudeChat(BaseChatAPI):
    default_model = "claude-3-5-sonnet-20240620"

    @classmethod
    def initialize(cls):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        return anthropic.Anthropic(api_key=api_key)

    def _convert_messages_to_claude_format(self):
        # Filter out system messages as they need to be handled separately
        messages = [msg.to_dict() for msg in self.messages 
                   if msg.role != MessageRole.SYSTEM]
        
        # Get the system message if it exists
        system_messages = [msg.content for msg in self.messages 
                         if msg.role == MessageRole.SYSTEM]
        system_prompt = system_messages[0] if system_messages else None

        return messages, system_prompt

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        
        messages, system_prompt = self._convert_messages_to_claude_format()
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.config.max_tokens or 1000,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=messages
        )
        
        assistant_message = response.content[0].text
        self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
        return assistant_message

    async def cleanup(self):
        pass