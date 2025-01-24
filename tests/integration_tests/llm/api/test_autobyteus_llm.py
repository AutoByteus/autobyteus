import pytest
from autobyteus.llm.api.autobyteus_llm import AutobyteusLLM
from autobyteus.llm.models import LLMModel, LLMProvider
import logging

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_autobyteus_integration():
    """Basic integration test with live Autobyteus service"""
    llm = AutobyteusLLM(model=LLMModel.GPT_4o_RPA)
    
    try:
        # Test simple message flow with corrected API usage
        response = await llm.send_user_message(
            user_message="Hello, please respond with 'pong'",
            user_message_index=0
        )
        
        # Maintain existing validation
        assert isinstance(response, str)
        
    finally:
        await llm.cleanup()

@pytest.mark.integration 
@pytest.mark.asyncio
async def test_streaming_integration():
    """Test streaming response from live service with corrected API"""
    llm = AutobyteusLLM(model=LLMModel.GPT_4o_RPA)
    
    try:
        # Update to stream_user_message with named parameters
        stream = llm.stream_user_message(
            user_message="Hello, write a short poem",
            user_message_index=0
        )
        full_response = ""
        
        # Preserve async iteration pattern
        async for chunk in stream:
            full_response += chunk
            
        assert len(full_response) > 20
        
    finally:
        await llm.cleanup()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling():
    """Test error response from service with API corrections"""
    llm = AutobyteusLLM(model=LLMModel.GPT_4o_RPA)
    
    try:
        with pytest.raises(Exception) as exc_info:
            # Update to send_user_message with proper parameters
            await llm.send_user_message(
                user_message="",  # Empty message trigger
                user_message_index=0
            )
            
        assert "validation" in str(exc_info.value).lower()
        
    finally:
        await llm.cleanup()
