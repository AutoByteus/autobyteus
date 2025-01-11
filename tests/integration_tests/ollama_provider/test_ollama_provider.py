import pytest
from autobyteus.llm.ollama_provider import OllamaModelProvider
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.providers import LLMProvider

def test_discover_and_register():
    """
    Integration test for OllamaModelProvider.discover_and_register.
    This test assumes a running Ollama client accessible via default settings.
    """
    # Clear the LLMFactory registry before test
    LLMFactory._models_by_provider = {}

    # Discover and register models from the Ollama provider
    OllamaModelProvider.discover_and_register()

    # Check that Ollama provider has registered models
    assert LLMProvider.OLLAMA in LLMFactory._models_by_provider, "No Ollama provider registered"
    ollama_models = LLMFactory._models_by_provider[LLMProvider.OLLAMA]
    assert len(ollama_models) > 0, "No models were registered from Ollama"

    # Check that each registered model has correct provider settings
    for model in ollama_models:
        assert model.provider == LLMProvider.OLLAMA
        assert model.value == model.name  # For Ollama, value should match name as per provider implementation
