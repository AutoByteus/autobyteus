import pytest
import logging
import os
import asyncio
from typing import Optional

import httpx

from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.models import LLMModel, ModelInfo
from autobyteus.llm.api.autobyteus_llm import AutobyteusLLM
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.utils.token_usage import TokenUsage

logger = logging.getLogger(__name__)
AUTOBYTEUS_API_KEY_ENV = "AUTOBYTEUS_API_KEY"
AUTOBYTEUS_SERVER_ENV = "AUTOBYTEUS_LLM_SERVER_URL"
AUTOBYTEUS_SSL_CERT_ENV = "AUTOBYTEUS_SSL_CERT_FILE"
AUTOBYTEUS_LLM_MODEL_ID_ENV = "AUTOBYTEUS_LLM_MODEL_ID"
AUTOBYTEUS_IMAGE_MODEL_ID_ENV = "AUTOBYTEUS_IMAGE_MODEL_ID"

# Helper to find a suitable model for testing
def find_autobyteus_model(is_image_model: bool = False) -> Optional[ModelInfo]:
    """Finds an available Autobyteus-hosted model from the factory."""
    api_key = os.getenv(AUTOBYTEUS_API_KEY_ENV)
    if not api_key:
        pytest.skip(f"{AUTOBYTEUS_API_KEY_ENV} not set. Skipping Autobyteus integration tests.")

    server_url = os.getenv(AUTOBYTEUS_SERVER_ENV, "https://api.autobyteus.com")
    ssl_cert_path = os.getenv(AUTOBYTEUS_SSL_CERT_ENV)
    verify_param = False
    if ssl_cert_path:
        if not os.path.exists(ssl_cert_path):
            pytest.skip(f"Custom SSL certificate not found at {ssl_cert_path}")
        verify_param = ssl_cert_path
    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
        headers = {"AUTOBYTEUS_API_KEY": api_key}
        response = httpx.get(
            f"{server_url.rstrip('/')}/models/llm",
            headers=headers,
            timeout=timeout,
            verify=verify_param,
        )
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(f"Autobyteus server unavailable: {exc}")

    LLMFactory.ensure_initialized()
    try:
        models = LLMFactory.list_models_by_runtime(LLMRuntime.AUTOBYTEUS)
    except Exception as exc:
        pytest.skip(f"Failed to discover Autobyteus models: {exc}")
    
    if not models:
        return None
        
    for model_info in models:
        is_preview = "preview" in model_info.display_name or "image" in model_info.display_name
        if is_image_model and is_preview:
            return model_info
        if not is_image_model and not is_preview:
            return model_info
            
    return None # Fallback if no specific type is found


def _get_model_info_by_identifier(model_identifier: str) -> Optional[ModelInfo]:
    LLMFactory.ensure_initialized()
    return next(
        (model for model in LLMFactory.list_available_models() if model.model_identifier == model_identifier),
        None,
    )

# Fixture to provide a text model, skipping if not available
@pytest.fixture(scope="module")
def text_model() -> ModelInfo:
    override_id = os.getenv(AUTOBYTEUS_LLM_MODEL_ID_ENV)
    if override_id:
        model = _get_model_info_by_identifier(override_id)
        if not model:
            pytest.skip(
                f"{AUTOBYTEUS_LLM_MODEL_ID_ENV}='{override_id}' was not found in the model registry."
            )
        return model

    model = find_autobyteus_model(is_image_model=False)
    if not model:
        pytest.skip("No suitable Autobyteus text model found for integration testing.")
    return model

# Fixture to provide an image model, skipping if not available
@pytest.fixture(scope="module")
def image_model() -> ModelInfo:
    override_id = os.getenv(AUTOBYTEUS_IMAGE_MODEL_ID_ENV)
    if override_id:
        model = _get_model_info_by_identifier(override_id)
        if not model:
            pytest.skip(
                f"{AUTOBYTEUS_IMAGE_MODEL_ID_ENV}='{override_id}' was not found in the model registry."
            )
        return model

    model = find_autobyteus_model(is_image_model=True)
    if not model:
        pytest.skip("No suitable Autobyteus image model found for integration testing.")
    return model

@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_autobyteus_integration(text_model: ModelInfo):
    """Basic integration test with a live Autobyteus service."""
    # Use the discovered model
    llm = LLMFactory.create_llm(text_model.model_identifier)
    
    try:
        user_input = LLMUserMessage(content="Hello, please respond with 'pong'")
        response = await asyncio.wait_for(
            llm.send_user_message(user_message=user_input),
            timeout=30.0
        )
        
        assert isinstance(response, CompleteResponse)
        assert isinstance(response.content, str)
        assert "pong" in response.content.lower()
        assert response.usage is not None
        
    finally:
        await llm.cleanup()

@pytest.mark.integration 
@pytest.mark.asyncio
async def test_streaming_integration(text_model: ModelInfo):
    """Test streaming response from a live service."""
    llm = LLMFactory.create_llm(text_model.model_identifier)
    
    try:
        user_input = LLMUserMessage(content="Hello, write a short poem")
        stream = llm.stream_user_message(user_message=user_input)
        full_response = ""
        final_chunk_received = False
        
        async def _consume_stream():
            nonlocal full_response, final_chunk_received
            async for chunk in stream:
                assert isinstance(chunk, ChunkResponse)
                assert isinstance(chunk.content, str)
                full_response += chunk.content
                
                if chunk.is_complete:
                    final_chunk_received = True
                    assert chunk.usage is not None

        await asyncio.wait_for(_consume_stream(), timeout=30.0)
            
        assert len(full_response) > 10, "Streamed response seems too short."
        assert final_chunk_received, "Stream did not yield a final chunk."
        
    finally:
        await llm.cleanup()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_streaming_with_image_url(image_model: ModelInfo):
    """
    Tests that image_urls are correctly received in streaming chunks from an
    Autobyteus-hosted image generation model.
    """
    llm = LLMFactory.create_llm(image_model.model_identifier)
    
    try:
        prompt = "Generate an image of a cat programming on a laptop."
        user_input = LLMUserMessage(content=prompt)
        stream = llm.stream_user_message(user_message=user_input)
        
        full_response_text = ""
        received_image_urls = []
        final_chunk_received = False

        async def _consume_stream():
            nonlocal full_response_text, received_image_urls, final_chunk_received
            async for chunk in stream:
                assert isinstance(chunk, ChunkResponse)
                
                if chunk.content:
                    full_response_text += chunk.content
                
                if chunk.image_urls:
                    received_image_urls.extend(chunk.image_urls)
                
                if chunk.is_complete:
                    final_chunk_received = True
                    assert chunk.usage is not None

        await asyncio.wait_for(_consume_stream(), timeout=45.0)

        assert final_chunk_received, "Stream did not complete with a final chunk."
        assert len(full_response_text) > 0, "Expected some descriptive text along with the image."
        assert len(received_image_urls) > 0, "No image URLs were received during the stream."
        
        # Validate URL format (assuming local test server)
        for url in received_image_urls:
            assert url.startswith(("http://", "https://")), f"Received invalid URL format: {url}"
        
        logger.info(f"Successfully received {len(received_image_urls)} image(s) via stream.")

    finally:
        await llm.cleanup()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling(text_model: ModelInfo):
    """Test error response from service with an invalid request."""
    llm = LLMFactory.create_llm(text_model.model_identifier)
    
    try:
        # Sending an empty message should trigger a validation error from the server
        with pytest.raises(Exception) as exc_info:
            user_input = LLMUserMessage(content="") 
            await asyncio.wait_for(
                llm.send_user_message(user_message=user_input),
                timeout=30.0
            )
            
        logger.debug(f"Error handling test caught exception: {exc_info.value}")
        error_message = str(exc_info.value).lower()
        # Server should return a 422 or similar for validation errors
        assert "validation" in error_message or \
               "empty" in error_message or \
               "input" in error_message or \
               "422" in error_message or \
               "llmusermessage" in error_message
        
    finally:
        await llm.cleanup()
