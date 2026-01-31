import pytest
import os
from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage

PLACEHOLDER_VALUES = {
    "YOUR_GEMINI_API_KEY",
    "YOUR_VERTEX_AI_PROJECT",
    "YOUR_VERTEX_AI_LOCATION",
}


def _is_missing(value: str) -> bool:
    return not value or value in PLACEHOLDER_VALUES

def _maybe_skip_gemini_error(exc: Exception) -> None:
    message = str(exc).lower()
    if "resource exhausted" in message or "429" in message or "quota" in message:
        pytest.skip(f"Gemini quota/rate limit: {exc}")

@pytest.fixture
def set_gemini_env(monkeypatch):
    """Ensure credentials are present for either Vertex AI or API-key mode.

    Priority matches initialize_gemini_client_with_runtime(): Vertex first, then API key.
    Skips the test suite cleanly if nothing usable is configured (via .env.test).
    """

    vertex_project = os.getenv("VERTEX_AI_PROJECT")
    vertex_location = os.getenv("VERTEX_AI_LOCATION")
    api_key = os.getenv("GEMINI_API_KEY")

    if not _is_missing(vertex_project) and not _is_missing(vertex_location):
        monkeypatch.setenv("VERTEX_AI_PROJECT", vertex_project)
        monkeypatch.setenv("VERTEX_AI_LOCATION", vertex_location)
        return "vertex"

    if not _is_missing(api_key):
        monkeypatch.setenv("GEMINI_API_KEY", api_key)
        return "api_key"

    pytest.skip(
        "Gemini credentials not set. Provide VERTEX_AI_PROJECT & VERTEX_AI_LOCATION "
        "for Vertex AI or GEMINI_API_KEY for API-key mode in .env.test"
    )

@pytest.fixture
def gemini_llm(set_gemini_env):
    # Use latest low-latency Gemini 3 Flash preview for coverage.
    return GeminiLLM(model=LLMModel['gemini-3-flash-preview'], llm_config=LLMConfig())

@pytest.mark.asyncio
async def test_gemini_llm_response(gemini_llm):
    user_message = LLMUserMessage(content="Hello, Gemini LLM!")
    try:
        response = await gemini_llm._send_user_message_to_llm(user_message)
    except Exception as exc:
        _maybe_skip_gemini_error(exc)
        raise
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_gemini_llm_streaming(gemini_llm):
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    try:
        async for chunk in gemini_llm._stream_user_message_to_llm(user_message):
            assert isinstance(chunk, ChunkResponse)
            if chunk.content:
                assert isinstance(chunk.content, str)
                received_tokens.append(chunk.content)
                complete_response += chunk.content

            if chunk.is_complete:
                if chunk.usage:
                    assert isinstance(chunk.usage, TokenUsage)
    except Exception as exc:
        _maybe_skip_gemini_error(exc)
        raise
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    await gemini_llm.cleanup()

@pytest.mark.asyncio
async def test_gemini_send_user_message(gemini_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    try:
        response_obj = await gemini_llm.send_user_message(user_message)
    except Exception as exc:
        _maybe_skip_gemini_error(exc)
        raise
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

@pytest.mark.asyncio
async def test_gemini_stream_user_message(gemini_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    try:
        async for chunk in gemini_llm.stream_user_message(user_message):
            assert isinstance(chunk, ChunkResponse)
            assert isinstance(chunk.content, str)
            received_tokens.append(chunk.content)
            complete_response += chunk.content
    except Exception as exc:
        _maybe_skip_gemini_error(exc)
        raise
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    await gemini_llm.cleanup()

@pytest.mark.asyncio
async def test_gemini_multimodal_image(gemini_llm):
    """Test sending an image to Gemini."""
    image_path = os.path.abspath("tests/assets/sample_image.png")
    # Ensure image exists
    if not os.path.exists(image_path):
        pytest.skip(f"Image not found at {image_path}")

    user_message = LLMUserMessage(
        content="Describe this image.",
        image_urls=[image_path]
    )
    try:
        response = await gemini_llm.send_user_message(user_message)
    except Exception as exc:
        _maybe_skip_gemini_error(exc)
        raise
    assert isinstance(response, CompleteResponse)
    print(f"\nResponse content: {response.content}\n")
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_gemini_multimodal_audio(gemini_llm):
    """Test sending audio to Gemini."""
    audio_path = os.path.abspath("tests/data/test_audio.mp3")
    if not os.path.exists(audio_path):
        pytest.skip(f"Audio file not found at {audio_path}")

    user_message = LLMUserMessage(
        content="Describe this audio.",
        audio_urls=[audio_path]
    )
    try:
        response = await gemini_llm.send_user_message(user_message)
    except Exception as exc:
        _maybe_skip_gemini_error(exc)
        raise
    assert isinstance(response, CompleteResponse)
    print(f"\nAudio Response content: {response.content}\n")
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_gemini_multimodal_video(gemini_llm):
    """Test sending video to Gemini."""
    video_path = os.path.abspath("tests/data/test_video.mp4")
    if not os.path.exists(video_path):
        pytest.skip(f"Video file not found at {video_path}")

    user_message = LLMUserMessage(
        content="Describe this video.",
        video_urls=[video_path]
    )
    try:
        response = await gemini_llm.send_user_message(user_message)
    except Exception as exc:
        _maybe_skip_gemini_error(exc)
        raise
    assert isinstance(response, CompleteResponse)
    print(f"\nVideo Response content: {response.content}\n")
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_gemini_llm_tool_calls(gemini_llm):
    """Test that Gemini LLM can generate tool calls in the stream."""
    from autobyteus.tools.registry import default_tool_registry
    from autobyteus.tools.usage.formatters.gemini_json_schema_formatter import GeminiJsonSchemaFormatter

    # 1. Setup Tool
    tool_def = default_tool_registry.get_tool_definition("write_file")
    assert tool_def
    formatter = GeminiJsonSchemaFormatter()
    # Note: GeminiLLM now handles auto-wrapping, so we pass raw schema
    tool_schema = formatter.provide(tool_def)
    
    # 2. Stream
    user_message = LLMUserMessage(content="Write a python file named tool_test.py with content 'print(1)'")
    
    tool_calls_found = False
    try:
        async for chunk in gemini_llm._stream_user_message_to_llm(
            user_message,
            tools=[tool_schema]
        ):
            if chunk.tool_calls:
                tool_calls_found = True
                for delta in chunk.tool_calls:
                    assert delta.name == "write_file"
                    assert delta.arguments_delta
                    print(f"Tool Call Delta: {delta}")
    except Exception as exc:
        _maybe_skip_gemini_error(exc)
        raise
    
    assert tool_calls_found, "Did not receive any tool calls from Gemini"
    
    await gemini_llm.cleanup()
