import pytest
import os
import logging

from autobyteus.tools.search.serper_strategy import SerperSearchStrategy

logger = logging.getLogger(__name__)

@pytest.fixture
def serper_strategy() -> SerperSearchStrategy:
    """
    Provides a SerperSearchStrategy instance.
    Skips the test if the SERPER_API_KEY environment variable is not configured.
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key or serper_api_key == "your_serper_api_key_here":
        pytest.skip("SERPER_API_KEY not set. Skipping Serper strategy integration tests.")
    
    return SerperSearchStrategy()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_serper_strategy_search(serper_strategy: SerperSearchStrategy):
    """
    Tests a direct search call to the SerperSearchStrategy.
    """
    query = "Benefits of using FastAPI"
    num_results = 3

    result = await serper_strategy.search(query, num_results)

    assert isinstance(result, str)
    # Serper results can have different structures, but 'Search Results' is common
    assert "Search Results:" in result or "Direct Answer" in result
    assert "Link:" in result
    
    logger.info(f"Serper Strategy Result:\n{result}")
