import pytest
import asyncio
from unittest.mock import patch
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.rate_limiter import RateLimiter
from autobyteus.llm.models import LLMModel

@pytest.fixture
def config():
    return LLMConfig(rate_limit=10, token_limit=1000)

@pytest.fixture
def rate_limiter(config):
    return RateLimiter(config)

@pytest.mark.rate_limiter
def test_initialization(rate_limiter, config):
    """Test if RateLimiter is initialized correctly."""
    assert rate_limiter.rate_limit == config.rate_limit
    assert rate_limiter.config == config

@pytest.mark.rate_limiter
@pytest.mark.asyncio
async def test_wait_if_needed_no_limit():
    """Test if wait_if_needed returns immediately when there's no rate limit."""
    config = LLMConfig(rate_limit=None)
    rate_limiter = RateLimiter(config)
    await rate_limiter.wait_if_needed()  # Should return immediately

@pytest.mark.rate_limiter
@pytest.mark.asyncio
async def test_wait_if_needed_with_limit(rate_limiter):
    """Test if wait_if_needed enforces the rate limit correctly."""
    with patch('asyncio.sleep') as mock_sleep:
        for _ in range(10):
            await rate_limiter.wait_if_needed()
        assert not mock_sleep.called
        
        await rate_limiter.wait_if_needed()
        assert mock_sleep.called

@pytest.mark.rate_limiter
@pytest.mark.asyncio
async def test_rate_limiting_behavior(rate_limiter):
    """Test the overall rate limiting behavior."""
    start_time = asyncio.get_event_loop().time()
    for _ in range(15):
        await rate_limiter.wait_if_needed()
    end_time = asyncio.get_event_loop().time()
    assert end_time - start_time >= 60  # At least one minute should have passed