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

class BedrockLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, system_message: str = None, custom_config: LLMConfig = None):
        super().__init__(model=model or LLMModel.BEDROCK_CLAUDE_3_5_SONNET_API, system_message=system_message, custom_config=custom_config)
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
    
    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0,
            "messages": [msg.to_dict() for msg in self.messages],
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
    
    async def cleanup(self):
        super().cleanup()
