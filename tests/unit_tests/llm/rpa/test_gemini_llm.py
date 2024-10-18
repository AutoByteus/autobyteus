import pytest
from autobyteus.llm.rpa.gemini_llm import GeminiChatLLM
from autobyteus.llm.models import LLMModel

@pytest.fixture
def llm_model():
    return LLMModel.GEMINI_1_0_PRO

@pytest.mark.asyncio
async def test_gemini_llm_initialization(llm_model):
    gemini_llm = GeminiChatLLM(llm_model)
    assert isinstance(gemini_llm, GeminiChatLLM)
    assert gemini_llm.model == llm_model
    assert gemini_llm.ui_integrator is not None

@pytest.mark.asyncio
async def test_send_user_message_success(llm_model):
    gemini_llm = GeminiChatLLM(llm_model)
    user_message = "Hello, Gemini!"
    response = await gemini_llm.send_user_message(user_message, user_message_index=0)
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_send_user_message_missing_index(llm_model):
    gemini_llm = GeminiChatLLM(llm_model)
    user_message = "Hello, Gemini!"
    with pytest.raises(ValueError, match="user_message_index is required in kwargs"):
        await gemini_llm.send_user_message(user_message)

@pytest.mark.asyncio
async def test_cleanup(llm_model):
    gemini_llm = GeminiChatLLM(llm_model)
    await gemini_llm.cleanup()
    # Since we can't directly check if ui_integrator is closed, we'll assume
    # no exception raised means successful cleanup