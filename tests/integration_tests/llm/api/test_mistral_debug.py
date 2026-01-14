import pytest
import os
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.tools.usage.formatters.mistral_json_schema_formatter import MistralJsonSchemaFormatter
from autobyteus.tools.registry import default_tool_registry

@pytest.fixture
def mistral_llm_non_stream():
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        pytest.skip("MISTRAL_API_KEY needed")
    return MistralLLM(model=LLMModel['mistral-large'])

@pytest.mark.asyncio
async def test_mistral_tool_call_non_stream(mistral_llm_non_stream):
    tool_def = default_tool_registry.get_tool_definition("write_file")
    formatter = MistralJsonSchemaFormatter()
    tool_schema = formatter.provide(tool_def)
    
    user_message = LLMUserMessage(content="Write a python file named mistral_test.py with content 'print(1)'")
    
    # We need to manually call _send_user_message_to_llm but passing tools?
    # MistralLLM._send_user_message_to_llm doesn't accept tools in kwargs currently?
    # I need to update it or call client directly.
    # Let's call client directly to verify SDK.
    
    mistral_messages = [{"role": "user", "content": "Write a python file named mistral_test.py with content 'print(1)'"}]
    
    print("\nSending non-streaming request...")
    response = await mistral_llm_non_stream.client.chat.complete_async(
        model=mistral_llm_non_stream.model.value,
        messages=mistral_messages,
        tools=[tool_schema]
    )
    print(f"Response: {response}")
    
    assert response.choices[0].message.tool_calls
