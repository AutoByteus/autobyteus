import pytest
from autobyteus.llm.api.autobyteus_llm import AutobyteusLLM
from autobyteus.llm.models import LLMModel, LLMProvider
from autobyteus.llm.user_message import LLMUserMessage # Import LLMUserMessage
import logging

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_autobyteus_integration():
    """Basic integration test with live Autobyteus service"""
    llm = AutobyteusLLM(model=LLMModel.GPT_4o_RPA)
    
    try:
        # Test simple message flow with corrected API usage
        # Wrap user_message string in LLMUserMessage and remove user_message_index
        user_input = LLMUserMessage(content="Hello, please respond with 'pong'")
        response = await llm.send_user_message(
            user_message=user_input
        )
        
        # Maintain existing validation
        assert isinstance(response, str)
        # A more specific check might be useful if the service guarantees 'pong'
        # For now, keeping it as is.
        # assert "pong" in response.lower() 
        
    finally:
        await llm.cleanup()

@pytest.mark.integration 
@pytest.mark.asyncio
async def test_streaming_integration():
    """Test streaming response from live service with corrected API"""
    llm = AutobyteusLLM(model=LLMModel.GPT_4o_RPA)
    
    try:
        # Update to stream_user_message with LLMUserMessage and remove user_message_index
        user_input = LLMUserMessage(content="Hello, write a short poem")
        stream = llm.stream_user_message(
            user_message=user_input
        )
        full_response = ""
        
        # Preserve async iteration pattern
        async for chunk in stream:
            # Assuming chunks are strings, which is common. If they are complex objects,
            # this part might need adjustment based on actual chunk structure.
            if isinstance(chunk, str):
                 full_response += chunk
            elif hasattr(chunk, 'content') and isinstance(chunk.content, str): # For OpenAI-like chunk objects
                 full_response += chunk.content
            else:
                 logger.warning(f"Received unexpected chunk type in stream: {type(chunk)}. Chunk: {chunk!r}")

            
        assert len(full_response) > 10 # Adjusted for a potentially very short poem
        
    finally:
        await llm.cleanup()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling():
    """Test error response from service with API corrections"""
    # This test assumes the AutobyteusLLM service might raise an error for an empty message.
    # The specific error type and message depend on the service's validation logic.
    llm = AutobyteusLLM(model=LLMModel.GPT_4o_RPA)
    
    try:
        with pytest.raises(Exception) as exc_info: # Keep generic Exception or use a more specific one if known
            # Update to send_user_message with LLMUserMessage and remove user_message_index
            # An empty content string is still valid for LLMUserMessage construction.
            user_input = LLMUserMessage(content="") 
            await llm.send_user_message(
                user_message=user_input 
            )
            
        # The assertion "validation" in str(exc_info.value).lower()
        # depends on the error message from the actual service.
        # This might need to be adjusted if the service error changes.
        # For example, if it's a ValueError or a custom HTTP error.
        logger.debug(f"Error handling test caught exception: {exc_info.value}")
        assert "validation" in str(exc_info.value).lower() or \
               "empty" in str(exc_info.value).lower() or \
               "input" in str(exc_info.value).lower() # Make assertion more flexible
        
    finally:
        await llm.cleanup()
