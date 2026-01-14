import pytest
import asyncio
import os
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from autobyteus.llm.api.lmstudio_llm import LMStudioLLM
from autobyteus.llm.lmstudio_provider import LMStudioModelProvider
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from openai import APIConnectionError

# Path to the test asset
TEST_IMAGE_PATH = "tests/assets/sample_image.png"
USER_PROVIDED_IMAGE_URL = "http://192.168.2.124:29695/rest/files/images/d0d0f29a-824c-4af0-9457-ecfba83ff9be.jpg"

@pytest.fixture
def set_lmstudio_env(monkeypatch):
    """Set the dummy API key required by the OpenAI client."""
    monkeypatch.setenv("LMSTUDIO_API_KEY", os.getenv("LMSTUDIO_API_KEY", "lm-studio"))
    # Also support host override for testing against specific servers
    host = os.getenv("LMSTUDIO_HOST")
    if host:
         monkeypatch.setenv("LMSTUDIO_HOST", host)

@pytest.fixture
def lmstudio_text_llm(set_lmstudio_env):
    """Fixture for text-only LM Studio model."""
    manual_model_id = os.getenv("LMSTUDIO_MODEL_ID")
    
    # Try manual first (legacy env var support)
    if manual_model_id:
        try:
            return _create_lmstudio_llm(manual_model_id)
        except Exception:
            pass # Fallback to discovery

    LLMFactory.reinitialize()
    models = LLMFactory.list_models_by_runtime(LLMRuntime.LMSTUDIO)
    if not models:
        pytest.skip("No LM Studio models found.")

    # Prioritize user-requested text model
    target_text_model = "qwen/qwen3-30b-a3b-2507"
    text_model = next((m for m in models if target_text_model in m.model_identifier), None)

    if not text_model:
        # Fallback: Pick first non-vision model
        text_model = next((m for m in models if "vl" not in m.model_identifier.lower()), models[0])
    
    return LLMFactory.create_llm(model_identifier=text_model.model_identifier)

@pytest.fixture
def lmstudio_vision_llm(set_lmstudio_env):
    """Fixture for vision-capable LM Studio model (specifically qwen/qwen3-vl-30b)."""
    target_vision_model = "qwen/qwen3-vl-30b"
    
    LLMFactory.reinitialize()
    models = LLMFactory.list_models_by_runtime(LLMRuntime.LMSTUDIO)
    
    # Look for exact match first
    vision_model = next((m for m in models if target_vision_model in m.model_identifier), None)
    
    # Fallback to broader vision keywords
    if not vision_model:
        # User requested to remove gemma/llava logic, specifically sticking to qwen-vl
        vision_keywords = ["vl"]
        vision_model = next((m for m in models if any(k in m.model_identifier.lower() for k in vision_keywords)), None)
    
    if not vision_model:
        pytest.skip(f"No vision model found (expected '{target_vision_model}' or keywords like 'vl').")
        
    return LLMFactory.create_llm(model_identifier=vision_model.model_identifier)

def _create_lmstudio_llm(model_id: str):
    """Helper to create LLM instance manually."""
    # We construct the model object manually to ensure it uses LMStudioLLM class
    # even if discovery didn't perfectly map it (though factory should handle it now).
    # NOTE: LLMFactory.create_llm accepts model_identifier string OR we can instantiate directly.
    # But usually we want the factory to manage it.
    # Here we simulate manual registration/creation if needed.
    
    llm_model = LLMModel(
        name=model_id,
        value=model_id,
        provider=LLMProvider.LMSTUDIO,
        llm_class=LMStudioLLM,
        canonical_name=model_id,
        runtime=LLMRuntime.LMSTUDIO,
        host_url=os.getenv("LMSTUDIO_HOST", LMStudioModelProvider.DEFAULT_LMSTUDIO_HOST),
        default_config=LLMConfig(pricing_config=TokenPricingConfig(0.0, 0.0))
    )
    # Directly call create_llm on the model object since factory might not have it registered
    return llm_model.create_llm()

@pytest.mark.asyncio
async def test_lmstudio_llm_response(lmstudio_text_llm):
    """Test a non-streaming response from an LM Studio text model."""
    user_message = LLMUserMessage(content="Hello! Please respond with 'pong'.")
    try:
        response = await lmstudio_text_llm.send_user_message(user_message)
        assert isinstance(response, CompleteResponse)
        assert isinstance(response.content, str)
        assert "pong" in response.content.lower()
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await lmstudio_text_llm.cleanup()

@pytest.mark.asyncio
@pytest.mark.parametrize("image_source", [
    TEST_IMAGE_PATH,
    USER_PROVIDED_IMAGE_URL
])
async def test_lmstudio_llm_multimodal_response(lmstudio_vision_llm, image_source):
    """Test a multimodal response from an LM Studio vision model."""
    if image_source == TEST_IMAGE_PATH and not os.path.exists(TEST_IMAGE_PATH):
        pytest.skip(f"Test image not found at {TEST_IMAGE_PATH}")
        
    user_message = LLMUserMessage(
        content="What is in this image? Describe it in one word.",
        image_urls=[image_source]
    )
    try:
        response = await lmstudio_vision_llm.send_user_message(user_message)
        assert isinstance(response, CompleteResponse)
        assert len(response.content) > 0
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await lmstudio_vision_llm.cleanup()

@pytest.mark.asyncio
async def test_lmstudio_llm_streaming(lmstudio_text_llm): 
    """Test a streaming response from an LM Studio text model."""
    user_message = LLMUserMessage(content="Write a short, two-sentence story about a robot.")
    complete_response = ""
    try:
        async for chunk in lmstudio_text_llm.stream_user_message(user_message):
            if chunk.content:
                complete_response += chunk.content
    
        assert len(complete_response) > 10
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await lmstudio_text_llm.cleanup()

@pytest.mark.asyncio
async def test_lmstudio_llm_tool_calls(lmstudio_text_llm):
    """Test tool call streaming from an LM Studio text model."""
    from autobyteus.tools.registry import default_tool_registry
    from autobyteus.tools.usage.formatters.openai_json_schema_formatter import OpenAiJsonSchemaFormatter
    
    tool_def = default_tool_registry.get_tool_definition("write_file")
    if not tool_def:
        pytest.fail("write_file tool definition not found")
        
    formatter = OpenAiJsonSchemaFormatter()
    tool_schema = formatter.provide(tool_def)
    
    user_message = LLMUserMessage(content="Please write a python script named 'hello_world.py' that prints 'Hello World'.")
    tool_calls_detected = 0
    
    try:
        async for chunk in lmstudio_text_llm.stream_user_message(user_message, tools=[tool_schema]):
            if chunk.tool_calls:
                tool_calls_detected += 1
                for tc in chunk.tool_calls:
                    # Normalized ToolCallDelta should have some data
                    assert tc.index is not None
        
        assert tool_calls_detected > 0, "Model did not generate any tool calls"

    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await lmstudio_text_llm.cleanup()
