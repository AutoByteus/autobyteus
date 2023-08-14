import pytest
from src.llm_integrations.openai_integration.openai_gpt_integration import OpenAIGPTIntegration
from src.llm_integrations.openai_integration.openai_api_factory import ApiType

@pytest.fixture
def openai_gpt_integration()-> OpenAIGPTIntegration:
    return OpenAIGPTIntegration(api_type=ApiType.CHAT)

# Marking the test to prevent automatic execution
@pytest.mark.skip(reason="Integration test calling the real OpenAI API")
def test_should_return_response_for_valid_input_messages(openai_gpt_integration):
    input_messages = [{"role": "user", "content": "What's the capital of France? Please only return the capital city, no extra words."}]
    response = openai_gpt_integration.process_input_messages(input_messages)
    assert response == "Paris"  # Expecting this response for the provided input message

def test_should_raise_exception_for_invalid_api_type():
    with pytest.raises(ValueError):
        OpenAIGPTIntegration(api_type="INVALID_API_TYPE")
