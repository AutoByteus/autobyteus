from typing import Dict, Optional, List
import boto3
import json
import os
from enum import Enum
from botocore.exceptions import ClientError
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from dotenv import load_dotenv

load_dotenv()

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"

class Message:
    def __init__(self, role: MessageRole, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}

class BedrockChat(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.client = self.initialize()
        self.model = model_name.value if model_name else "anthropic.claude-3-5-sonnet-20240620-v1:0"
        self.system_message = system_message
        self.messages = []
        super().__init__(model=self.model)

    @classmethod
    def initialize(cls):
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        region = os.environ.get("AWS_REGION", "us-east-1")

        if not (aws_access_key and aws_secret_key):
            raise ValueError(
                "AWS credentials not found. Please set AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY environment variables."
            )

        try:
            return boto3.client(
                service_name='bedrock-runtime',
                region_name=region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Bedrock client: {str(e)}")

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0,
            "messages": [msg.to_dict() for msg in self.messages],
            "system": self.system_message if self.system_message else ""
        })

        try:
            response = self.client.invoke_model(
                modelId=self.model,
                body=request_body
            )
            response_body = json.loads(response['body'].read())
            assistant_message = response_body['content'][0]['text']
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise ValueError(f"Bedrock API error: {error_code} - {error_message}")
        except Exception as e:
            raise ValueError(f"Error in Bedrock API call: {str(e)}")

    async def cleanup(self):
        pass