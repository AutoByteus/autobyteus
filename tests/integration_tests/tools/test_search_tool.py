import pytest
import os
import logging
from typing import Generator

from autobyteus.tools.search_tool import Search
from autobyteus.tools.search.factory import SearchClientFactory
from autobyteus.tools.search.providers import SearchProvider
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterType
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)


def _reset_factory_singleton():
    SearchClientFactory._instance = None
    SingletonMeta._instances.pop(SearchClientFactory, None)


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
    _reset_factory_singleton()
    yield Search()
    _reset_factory_singleton()


@pytest.fixture
def vertex_ai_search_tool(monkeypatch) -> Generator[Search, None, None]:
    """
    Provides a Search tool instance configured to use the Vertex AI Search strategy.
    Skips the test if VERTEX_AI_SEARCH_API_KEY or VERTEX_AI_SEARCH_SERVING_CONFIG are not configured.
    """
    vertex_api_key = os.getenv("VERTEX_AI_SEARCH_API_KEY")
    vertex_serving_config = os.getenv("VERTEX_AI_SEARCH_SERVING_CONFIG")

    if not all([vertex_api_key, vertex_serving_config]):
        pytest.skip(
            "VERTEX_AI_SEARCH_API_KEY or VERTEX_AI_SEARCH_SERVING_CONFIG not set. "
            "Skipping Vertex AI Search integration tests."
        )

    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", SearchProvider.VERTEX_AI_SEARCH.value)
    _reset_factory_singleton()
    yield Search()
    _reset_factory_singleton()


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
async def test_search_tool_with_vertex_ai_search(vertex_ai_search_tool: Search):
    """
    Integration test for the Search tool using the Vertex AI Search provider.
    """
    query = "What is Python programming language?"
    mock_context = type("AgentContext", (), {"agent_id": "test_agent"})()

    result = await vertex_ai_search_tool._execute(context=mock_context, query=query, num_results=3)

    assert isinstance(result, str)
    assert (
        "Search Results:" in result
        or result == "No relevant information found for the query via Vertex AI Search."
    )
    logger.info(f"Search Tool (Vertex AI Search) result:\n{result}")
