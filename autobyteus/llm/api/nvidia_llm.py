
import logging
from typing import Dict, Optional, List, AsyncGenerator
from openai import OpenAI
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

logger = logging.getLogger(__name__)

class NvidiaLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, system_message: str = None, custom_config: LLMConfig = None):
        super().__init__(model=model or LLMModel.NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_API, system_message=system_message, custom_config=custom_config)
        self.client = self.initialize()
    
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
    
    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
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
            self.add_assistant_message(assistant_message)
            
            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
            
            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            raise ValueError(f"Error in Nvidia API call: {str(e)}")
    
    async def stream_response(self, user_message: str) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        complete_response = ""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in self.messages],
                temperature=0,
                top_p=1,
                max_tokens=1024,
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    token = chunk.choices[0].delta.content
                    complete_response += token
                    yield ChunkResponse(
                        content=token,
                        is_complete=False
                    )
            
            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
            
            yield ChunkResponse(
                content="",
                is_complete=True,
                usage=token_usage
            )

            self.add_assistant_message(complete_response)
        except Exception as e:
            raise ValueError(f"Error in Nvidia API streaming call: {str(e)}")
    
    async def cleanup(self):
        super().cleanup()
