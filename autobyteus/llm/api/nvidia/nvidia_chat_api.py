# nvidia_chat_api.py
import os
from openai import OpenAI
from typing import Optional, List

from autobyteus.llm.api.base_chat import BaseChatAPI, Message, MessageRole

class NvidiaChat(BaseChatAPI):
    default_model = "nvidia/llama-3.1-nemotron-70b-instruct"

    @classmethod
    def initialize(cls):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY not set")
        return OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[msg.to_dict() for msg in self.messages],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens or 1024,
            top_p=self.config.top_p or 1,
            **self.config.extra_params
        )
        assistant_message = completion.choices[0].message.content
        self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
        return assistant_message

    async def cleanup(self):
        pass