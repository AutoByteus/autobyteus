import pytest

from autobyteus.tools.search.factory import SearchClientFactory
from autobyteus.tools.search.serper_strategy import SerperSearchStrategy
from autobyteus.tools.search.serpapi_strategy import SerpApiSearchStrategy
from autobyteus.tools.search.vertex_ai_search_strategy import VertexAISearchStrategy
from autobyteus.tools.search.providers import SearchProvider
from autobyteus.utils.singleton import SingletonMeta


def _clear_search_env(monkeypatch):
    monkeypatch.delenv("DEFAULT_SEARCH_PROVIDER", raising=False)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.delenv("VERTEX_AI_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("VERTEX_AI_SEARCH_SERVING_CONFIG", raising=False)


def _reset_factory_singleton():
    SearchClientFactory._instance = None
    SingletonMeta._instances.pop(SearchClientFactory, None)


def test_factory_creates_serper_client(monkeypatch):
    """
    Unit test to ensure the factory selects SerperStrategy when configured.
    """
    _clear_search_env(monkeypatch)
    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", SearchProvider.SERPER.value)
    monkeypatch.setenv("SERPER_API_KEY", "fake-serper-key")
    
    # Reset singleton to force re-initialization
    _reset_factory_singleton()
    
    factory = SearchClientFactory()
    client = factory.create_search_client()
    
    assert isinstance(client._strategy, SerperSearchStrategy)
    
    # Cleanup
    _reset_factory_singleton()

def test_factory_creates_serpapi_client(monkeypatch):
    """
    Unit test to ensure the factory selects SerpApiSearchStrategy when configured.
    """
    _clear_search_env(monkeypatch)
    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", SearchProvider.SERPAPI.value)
    monkeypatch.setenv("SERPAPI_API_KEY", "fake-serpapi-key")

    _reset_factory_singleton()
    factory = SearchClientFactory()
    client = factory.create_search_client()
    
    assert isinstance(client._strategy, SerpApiSearchStrategy)
    _reset_factory_singleton()

def test_factory_creates_vertex_ai_search_client(monkeypatch):
    """
    Unit test to ensure the factory selects VertexAISearchStrategy when configured.
    """
    _clear_search_env(monkeypatch)
    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", SearchProvider.VERTEX_AI_SEARCH.value)
    monkeypatch.setenv("VERTEX_AI_SEARCH_API_KEY", "fake-vertex-key")
    monkeypatch.setenv(
        "VERTEX_AI_SEARCH_SERVING_CONFIG",
        "projects/p/locations/global/collections/default_collection/engines/e/servingConfigs/default_search",
    )

    _reset_factory_singleton()
    factory = SearchClientFactory()
    client = factory.create_search_client()
    
    assert isinstance(client._strategy, VertexAISearchStrategy)
    _reset_factory_singleton()

def test_factory_falls_back_to_serper(monkeypatch):
    """
    Unit test to ensure the factory falls back to Serper if no provider is set but Serper is configured.
    """
    _clear_search_env(monkeypatch)
    monkeypatch.setenv("SERPER_API_KEY", "fake-serper-key")

    _reset_factory_singleton()
    factory = SearchClientFactory()
    client = factory.create_search_client()
    
    assert isinstance(client._strategy, SerperSearchStrategy)
    _reset_factory_singleton()


def test_factory_falls_back_to_serpapi(monkeypatch):
    """
    Unit test to ensure the factory falls back to SerpApi when Serper is not configured.
    """
    _clear_search_env(monkeypatch)
    monkeypatch.setenv("SERPAPI_API_KEY", "fake-serpapi-key")

    _reset_factory_singleton()
    factory = SearchClientFactory()
    client = factory.create_search_client()

    assert isinstance(client._strategy, SerpApiSearchStrategy)
    _reset_factory_singleton()


def test_factory_falls_back_to_vertex_ai_search(monkeypatch):
    """
    Unit test to ensure the factory falls back to Vertex AI Search when Serper and SerpApi are not configured.
    """
    _clear_search_env(monkeypatch)
    monkeypatch.setenv("VERTEX_AI_SEARCH_API_KEY", "fake-vertex-key")
    monkeypatch.setenv(
        "VERTEX_AI_SEARCH_SERVING_CONFIG",
        "projects/p/locations/global/collections/default_collection/engines/e/servingConfigs/default_search",
    )

    _reset_factory_singleton()
    factory = SearchClientFactory()
    client = factory.create_search_client()

    assert isinstance(client._strategy, VertexAISearchStrategy)
    _reset_factory_singleton()

def test_factory_raises_error_when_misconfigured(monkeypatch):
    """
    Unit test to ensure the factory raises a ValueError if no providers are configured.
    """
    _clear_search_env(monkeypatch)
    
    _reset_factory_singleton()
    factory = SearchClientFactory()
    
    with pytest.raises(ValueError, match="No search provider is configured"):
        factory.create_search_client()
    
    _reset_factory_singleton()


def test_factory_raises_error_for_removed_google_cse_provider(monkeypatch):
    """
    Unit test to ensure the factory raises an error for removed google_cse provider.
    """
    _clear_search_env(monkeypatch)
    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", "google_cse")

    SearchClientFactory._instance = None
    factory = SearchClientFactory()

    with pytest.raises(ValueError, match="DEFAULT_SEARCH_PROVIDER 'google_cse' is no longer supported"):
        factory.create_search_client()

    SearchClientFactory._instance = None
