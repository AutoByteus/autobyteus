# bedrock_chat_api.py
import os
import json
import boto3
from typing import Optional, List

from autobyteus.llm.api.base_chat import BaseChatAPI, Message, MessageRole

class BedrockChat(BaseChatAPI):
    default_model = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    @classmethod
    def initialize(cls):
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", "us-east-1")
        if not (aws_access_key and aws_secret_key):
            raise ValueError("AWS credentials not set")
        return boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.max_tokens or 1000,
            "temperature": self.config.temperature,
            "messages": [msg.to_dict() for msg in self.messages],
            "system": self.config.system_message
        })
        response = self.client.invoke_model(
            modelId=self.model,
            body=request_body
        )
        response_body = json.loads(response['body'].read())
        assistant_message = response_body['content'][0]['text']
        self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
        return assistant_message

    async def cleanup(self):
        pass