import pytest
import os
import logging
from typing import Generator

from autobyteus.tools.search_tool import Search
from autobyteus.tools.search.factory import SearchClientFactory
from autobyteus.tools.search.providers import SearchProvider
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterType

logger = logging.getLogger(__name__)

@pytest.fixture
def serper_search_tool(monkeypatch) -> Generator[Search, None, None]:
    """
    Provides a Search tool instance configured to use the Serper strategy.
    Skips the test if the SERPER_API_KEY is not configured.
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key or serper_api_key == "your_serper_api_key_here":
        pytest.skip("SERPER_API_KEY not set. Skipping Serper search integration tests.")

    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", SearchProvider.SERPER.value)
    SearchClientFactory._instance = None
    yield Search()
    SearchClientFactory._instance = None


@pytest.fixture
def google_cse_search_tool(monkeypatch) -> Generator[Search, None, None]:
    """
    Provides a Search tool instance configured to use the Google CSE strategy.
    Skips the test if GOOGLE_CSE_API_KEY or GOOGLE_CSE_ID are not configured.
    """
    google_api_key = os.getenv("GOOGLE_CSE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")

    if not all([google_api_key, google_cse_id]) or \
       google_api_key == "your_google_cse_api_key_here" or \
       google_cse_id == "your_google_cse_id_here":
        pytest.skip("GOOGLE_CSE_API_KEY or GOOGLE_CSE_ID not set. Skipping Google CSE integration tests.")

    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", SearchProvider.GOOGLE_CSE.value)
    SearchClientFactory._instance = None
    yield Search()
    SearchClientFactory._instance = None


def test_search_schema():
    """Tests that the Search tool has a valid schema."""
    schema = Search.get_argument_schema()
    assert isinstance(schema, ParameterSchema)
    
    params = {p.name: p for p in schema.parameters}
    assert "query" in params
    assert params["query"].param_type == ParameterType.STRING
    assert params["query"].required is True
    
    assert "num_results" in params
    assert params["num_results"].param_type == ParameterType.INTEGER
    assert params["num_results"].required is False

@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tool_with_serper(serper_search_tool: Search):
    """
    Integration test for the Search tool using the Serper provider.
    """
    query = "What is the capital of France?"
    mock_context = type("AgentContext", (), {"agent_id": "test_agent"})()

    result = await serper_search_tool._execute(context=mock_context, query=query, num_results=3)

    assert isinstance(result, str)
    assert "Paris" in result
    assert "Search Results:" in result
    logger.info(f"Search Tool (Serper) result:\n{result}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tool_with_google_cse(google_cse_search_tool: Search):
    """
    Integration test for the Search tool using the Google CSE provider.
    """
    query = "What is Python programming language?"
    mock_context = type("AgentContext", (), {"agent_id": "test_agent"})()

    result = await google_cse_search_tool._execute(context=mock_context, query=query, num_results=3)

    assert isinstance(result, str)
    assert "Search Results:" in result
    assert "Link:" in result
    logger.info(f"Search Tool (Google CSE) result:\n{result}")
