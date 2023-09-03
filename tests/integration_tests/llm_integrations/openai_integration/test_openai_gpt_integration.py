import pytest
from autobyteus.llm_integrations.openai_integration.openai_gpt_integration import OpenAIGPTIntegration
from autobyteus.llm_integrations.openai_integration.openai_api_factory import ApiType
from autobyteus.llm_integrations.openai_integration.openai_models import OpenAIModel


@pytest.mark.skip(reason="Integration test which may call the real OpenAI API")
def test_initialization_with_gpt_3_5_turbo_model():
    """Integration test to ensure correct initialization with GPT_3_5_TURBO model."""
    integration = OpenAIGPTIntegration(api_type=ApiType.CHAT, model_name=OpenAIModel.GPT_3_5_TURBO)
    assert integration.openai_api.model_name == OpenAIModel.GPT_3_5_TURBO

@pytest.mark.skip(reason="Integration test which may call the real OpenAI API")
def test_process_input_messages_integration():
    """Integration test to ensure correct processing of input messages."""
    integration = OpenAIGPTIntegration(api_type=ApiType.CHAT, model_name=OpenAIModel.GPT_3_5_TURBO)

    questions = [
        "What is the capital of France? No extra words, only the answer please.",
    ]

    result = integration.process_input_messages(questions)

    # Let's keep the assertions general since exact phrasing can vary.
    assert "Paris" in result
