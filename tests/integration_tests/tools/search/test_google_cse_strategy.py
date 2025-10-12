import pytest
import os
import logging

from autobyteus.tools.search.google_cse_strategy import GoogleCSESearchStrategy

logger = logging.getLogger(__name__)

@pytest.fixture
def google_cse_strategy() -> GoogleCSESearchStrategy:
    """
    Provides a GoogleCSESearchStrategy instance.
    Skips the test if the necessary environment variables are not configured.
    """
    google_api_key = os.getenv("GOOGLE_CSE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")

    if not all([google_api_key, google_cse_id]) or \
       google_api_key == "your_google_cse_api_key_here" or \
       google_cse_id == "your_google_cse_id_here":
        pytest.skip("GOOGLE_CSE_API_KEY or GOOGLE_CSE_ID not set. Skipping Google CSE strategy integration tests.")
    
    return GoogleCSESearchStrategy()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_google_cse_strategy_search(google_cse_strategy: GoogleCSESearchStrategy):
    """
    Tests a direct search call to the GoogleCSESearchStrategy.
    """
    query = "What is the Python Global Interpreter Lock?"
    num_results = 2

    result = await google_cse_strategy.search(query, num_results)

    assert isinstance(result, str)
    assert "Search Results:" in result
    assert "Link:" in result
    assert "Snippet:" in result
    # Check if it respected the num_results parameter
    assert "1." in result
    assert "2." in result
    assert "3." not in result

    logger.info(f"Google CSE Strategy Result:\n{result}")
