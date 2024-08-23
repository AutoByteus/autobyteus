# File: autobyteus/tests/unit_tests/llm/test_gemini_llm.py

import pytest
import os
from autobyteus.llm.api.google.gemini_llm import GeminiLLM

@pytest.fixture(scope="module")
def gemini_llm():
    # Set the API key as an environment variable
    os.environ["GEMINI_API_KEY"] = "AIzaSyBw_kNm_HGGvIC_HSZEnEQzxNIm8ZAIuAg"
    
    # Create and yield the GeminiLLM instance
    llm = GeminiLLM("gemini-1.5-flash")
    yield llm
    
    # Clean up: remove the environment variable after tests
    del os.environ["GEMINI_API_KEY"]

@pytest.mark.asyncio
async def test_gemini_llm_initialization(gemini_llm):
    assert isinstance(gemini_llm, GeminiLLM)
    assert gemini_llm.model.model_name == "gemini-1.5-flash"

@pytest.mark.asyncio
async def test_send_user_message(gemini_llm):
    user_message = "Hello, how are you?"
    response = await gemini_llm.send_user_message(user_message)
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_cleanup(gemini_llm):
    # Since cleanup is currently empty, we just ensure it doesn't raise any exceptions
    await gemini_llm.cleanup()