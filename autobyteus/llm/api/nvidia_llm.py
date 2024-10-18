from typing import Dict, Optional, List
from openai import OpenAI
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message

class NvidiaLLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.client = self.initialize()
        self.model = model_name.value if model_name else "nvidia/llama-3.1-nemotron-70b-instruct"
        self.messages = []
        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))
        super().__init__(model=self.model)

    @classmethod
    def initialize(cls):
        nvidia_api_key = os.environ.get("NVIDIA_API_KEY")
        if not nvidia_api_key:
            raise ValueError(
                "NVIDIA_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            return OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=nvidia_api_key
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Nvidia client: {str(e)}")

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in self.messages],
                temperature=0,
                top_p=1,
                max_tokens=1024,
                stream=False
            )
            assistant_message = completion.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except Exception as e:
            raise ValueError(f"Error in Nvidia API call: {str(e)}")

    async def stream_response(self, user_message: str) -> str:
        """Optional method for streaming responses"""
        self.messages.append(Message(MessageRole.USER, user_message))
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in self.messages],
                temperature=0,
                top_p=1,
                max_tokens=1024,
                stream=True
            )
            
            full_response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content

            self.messages.append(Message(MessageRole.ASSISTANT, full_response))
            return full_response
        except Exception as e:
            raise ValueError(f"Error in Nvidia API streaming call: {str(e)}")

    async def cleanup(self):
        pass