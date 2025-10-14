import pytest
from unittest.mock import patch

from autobyteus.tools.search.factory import SearchClientFactory
from autobyteus.tools.search.serper_strategy import SerperSearchStrategy
from autobyteus.tools.search.google_cse_strategy import GoogleCSESearchStrategy
from autobyteus.tools.search.providers import SearchProvider

def test_factory_creates_serper_client(monkeypatch):
    """
    Unit test to ensure the factory selects SerperStrategy when configured.
    """
    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", SearchProvider.SERPER.value)
    monkeypatch.setenv("SERPER_API_KEY", "fake-serper-key")
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "fake-google-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "fake-google-id")
    
    # Reset singleton to force re-initialization
    SearchClientFactory._instance = None
    
    factory = SearchClientFactory()
    client = factory.create_search_client()
    
    assert isinstance(client._strategy, SerperSearchStrategy)
    
    # Cleanup
    SearchClientFactory._instance = None

def test_factory_creates_google_cse_client(monkeypatch):
    """
    Unit test to ensure the factory selects GoogleCSESearchStrategy when configured.
    """
    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", SearchProvider.GOOGLE_CSE.value)
    monkeypatch.setenv("SERPER_API_KEY", "fake-serper-key")
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "fake-google-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "fake-google-id")

    SearchClientFactory._instance = None
    factory = SearchClientFactory()
    client = factory.create_search_client()
    
    assert isinstance(client._strategy, GoogleCSESearchStrategy)
    SearchClientFactory._instance = None

def test_factory_falls_back_to_serper(monkeypatch):
    """
    Unit test to ensure the factory falls back to Serper if no provider is set but Serper is configured.
    """
    monkeypatch.delenv("DEFAULT_SEARCH_PROVIDER", raising=False)
    monkeypatch.setenv("SERPER_API_KEY", "fake-serper-key")
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "fake-google-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "fake-google-id")

    SearchClientFactory._instance = None
    factory = SearchClientFactory()
    client = factory.create_search_client()
    
    assert isinstance(client._strategy, SerperSearchStrategy)
    SearchClientFactory._instance = None

def test_factory_falls_back_to_google_cse(monkeypatch):
    """
    Unit test to ensure the factory falls back to Google CSE if Serper is not configured.
    """
    monkeypatch.delenv("DEFAULT_SEARCH_PROVIDER", raising=False)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CSE_API_KEY", "fake-google-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "fake-google-id")

    SearchClientFactory._instance = None
    factory = SearchClientFactory()
    client = factory.create_search_client()
    
    assert isinstance(client._strategy, GoogleCSESearchStrategy)
    SearchClientFactory._instance = None

def test_factory_raises_error_when_misconfigured(monkeypatch):
    """
    Unit test to ensure the factory raises a ValueError if no providers are configured.
    """
    monkeypatch.delenv("DEFAULT_SEARCH_PROVIDER", raising=False)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_ID", raising=False)
    
    SearchClientFactory._instance = None
    factory = SearchClientFactory()
    
    with pytest.raises(ValueError, match="No search provider is configured"):
        factory.create_search_client()
    
    SearchClientFactory._instance = None
