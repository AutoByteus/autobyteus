from typing import Dict, Optional, List, AsyncGenerator
import boto3
import json
import os
from botocore.exceptions import ClientError
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.user_message import LLMUserMessage

class BedrockLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        if model is None:
            model = LLMModel.BEDROCK_CLAUDE_3_5_SONNET_API
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        self.client = self.initialize()
    
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
    
    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        
        # NOTE: This implementation does not yet support multimodal inputs for Bedrock.
        # It will only send the text content.
        
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0,
            "messages": [msg.to_dict() for msg in self.messages if msg.role != MessageRole.SYSTEM],
            "system": self.system_message if self.system_message else ""
        })

        try:
            response = self.client.invoke_model(
                modelId=self.model.value,
                body=request_body
            )
            response_body = json.loads(response['body'].read())
            assistant_message = response_body['content'][0]['text']
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
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise ValueError(f"Bedrock API error: {error_code} - {error_message}")
        except Exception as e:
            raise ValueError(f"Error in Bedrock API call: {str(e)}")

    async def _stream_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        # Placeholder for future implementation
        response = await self._send_user_message_to_llm(user_message, **kwargs)
        yield ChunkResponse(content=response.content, is_complete=True, usage=response.usage)

    async def cleanup(self):
        await super().cleanup()
