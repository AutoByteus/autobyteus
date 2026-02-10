import logging
import os

import pytest

from autobyteus.tools.search.vertex_ai_search_strategy import VertexAISearchStrategy

logger = logging.getLogger(__name__)


@pytest.fixture
def vertex_ai_search_strategy() -> VertexAISearchStrategy:
    """
    Provides a VertexAISearchStrategy instance.
    Skips the test if required Vertex AI Search environment variables are not configured.
    """
    api_key = os.getenv("VERTEX_AI_SEARCH_API_KEY")
    serving_config = os.getenv("VERTEX_AI_SEARCH_SERVING_CONFIG")

    if not api_key or not serving_config:
        pytest.skip(
            "VERTEX_AI_SEARCH_API_KEY or VERTEX_AI_SEARCH_SERVING_CONFIG not set. "
            "Skipping Vertex AI Search strategy integration tests."
        )

    return VertexAISearchStrategy()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vertex_ai_search_strategy_search(vertex_ai_search_strategy: VertexAISearchStrategy):
    """
    Tests a direct search call to the VertexAISearchStrategy.
    """
    query = "What is the Python Global Interpreter Lock?"
    num_results = 2

    result = await vertex_ai_search_strategy.search(query, num_results)

    assert isinstance(result, str)
    assert result.startswith("Search Results:") or result == "No relevant information found for the query via Vertex AI Search."

    logger.info(f"Vertex AI Search Strategy Result:\n{result}")
