import pytest
from autobyteus.llm.api.autobyteus_llm import AutobyteusLLM
from autobyteus.llm.models import LLMModel, LLMProvider
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse # Added import
from autobyteus.llm.utils.token_usage import TokenUsage # Added import
import logging

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_autobyteus_integration():
    """Basic integration test with live Autobyteus service"""
    llm = AutobyteusLLM(model=LLMModel['value'])
    
    try:
        # Test simple message flow with corrected API usage
        user_input = LLMUserMessage(content="Hello, please respond with 'pong'")
        response = await llm.send_user_message(
            user_message=user_input
        )
        
        # Changed assertion to check CompleteResponse object
        assert isinstance(response, CompleteResponse)
        assert isinstance(response.content, str)
        assert "pong" in response.content.lower() # More specific check
        assert response.usage is not None # Expecting usage data
        
    finally:
        await llm.cleanup()

@pytest.mark.integration 
@pytest.mark.asyncio
async def test_streaming_integration():
    """Test streaming response from live service with corrected API"""
    llm = AutobyteusLLM(model=LLMModel['value'])
    
    try:
        # Update to stream_user_message with LLMUserMessage
        user_input = LLMUserMessage(content="Hello, write a short poem")
        stream = llm.stream_user_message(
            user_message=user_input
        )
        full_response = ""
        
        # Preserve async iteration pattern, adjust to ChunkResponse
        async for chunk in stream:
            assert isinstance(chunk, ChunkResponse) # Expect ChunkResponse object
            assert isinstance(chunk.content, str)
            full_response += chunk.content
            
            # The final chunk in a stream should contain usage data
            if chunk.is_complete:
                assert chunk.usage is not None # Expect usage in the final chunk
            
        assert len(full_response) > 10
        
    finally:
        await llm.cleanup()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling():
    """Test error response from service with API corrections"""
    llm = AutobyteusLLM(model=LLMModel['value'])
    
    try:
        with pytest.raises(Exception) as exc_info:
            user_input = LLMUserMessage(content="") 
            await llm.send_user_message(
                user_message=user_input 
            )
            
        logger.debug(f"Error handling test caught exception: {exc_info.value}")
        assert "validation" in str(exc_info.value).lower() or \
               "empty" in str(exc_info.value).lower() or \
               "input" in str(exc_info.value).lower()
        
    finally:
        await llm.cleanup()
