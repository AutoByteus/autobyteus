import pytest
import asyncio
import os
from autobyteus.llm.api.bedrock_llm import BedrockLLM

@pytest.fixture
def set_bedrock_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "YOUR_AWS_ACCESS_KEY_ID")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "YOUR_AWS_SECRET_ACCESS_KEY")

@pytest.fixture
def bedrock_llm(set_bedrock_env):
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not aws_access_key or not aws_secret_key:
        pytest.skip("AWS credentials not set. Skipping BedrockLLM tests.")
    model_name = None  # Use default model
    system_message = "You are a helpful assistant."
    return BedrockLLM(model_name=model_name, system_message=system_message)

@pytest.mark.asyncio
async def test_bedrock_llm_response(bedrock_llm):
    user_message = "Hello, Bedrock LLM!"
    response = await bedrock_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, str)
    assert len(response) > 0
