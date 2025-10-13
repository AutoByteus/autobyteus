import pytest
import os
import logging

from autobyteus.tools.search.serpapi_strategy import SerpApiSearchStrategy

logger = logging.getLogger(__name__)

@pytest.fixture
def serpapi_strategy() -> SerpApiSearchStrategy:
    """
    Provides a SerpApiSearchStrategy instance.
    Skips the test if the SERPAPI_API_KEY environment variable is not configured.
    """
    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_api_key or serpapi_api_key == "your_serpapi_api_key_here":
        pytest.skip("SERPAPI_API_KEY not set. Skipping SerpApi strategy integration tests.")
    
    return SerpApiSearchStrategy()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_serpapi_strategy_search(serpapi_strategy: SerpApiSearchStrategy):
    """
    Tests a direct search call to the SerpApiSearchStrategy.
    """
    query = "What is asynchronous programming?"
    num_results = 2

    result = await serpapi_strategy.search(query, num_results)

    assert isinstance(result, str)
    assert "Search Results:" in result
    assert "Link:" in result
    assert "Snippet:" in result
    # Check if it respected the num_results parameter
    assert "1." in result
    assert "2." in result
    assert "3." not in result

    logger.info(f"SerpApi Strategy Result:\n{result}")
