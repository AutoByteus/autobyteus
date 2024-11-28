from typing import Optional, List
from anthropic import AnthropicBedrock
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message

class BedrockLLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.client = self.initialize()
        self.model = model_name.value if model_name else "anthropic.claude-3-5-sonnet-20240620-v1:0"
        self.system_message = system_message or "You are a helpful assistant."
        self.messages = []
        super().__init__(model=self.model)

    @classmethod
    def initialize(cls):
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("AWS_REGION", "us-west-2")

        try:
            return AnthropicBedrock(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_region=aws_region
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Bedrock client: {str(e)}")

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0,
                system=self.system_message,
                messages=[msg.to_dict() for msg in self.messages]
            )
            assistant_message = response.content[0].text
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
            
        except Exception as e:
            raise ValueError(f"Error in Bedrock API call: {str(e)}")

    async def cleanup(self):
        pass