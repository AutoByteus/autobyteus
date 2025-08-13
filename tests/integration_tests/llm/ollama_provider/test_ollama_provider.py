import pytest
import os
from autobyteus.llm.ollama_provider import OllamaModelProvider
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.runtimes import LLMRuntime

@pytest.fixture(autouse=True)
def check_ollama_env():
    """
    Fixture to skip all tests in this module if Ollama is not configured.
    This runs automatically for each test in the module.
    """
    if not os.getenv("OLLAMA_HOSTS") or os.getenv("CI"):
        pytest.skip("Requires OLLAMA_HOSTS to be set and a running Ollama instance, skipped in CI.")


def test_discover_and_register_ollama_models():
    """
    Integration test for OllamaModelProvider.discover_and_register.
    Assumes a running Ollama client accessible via OLLAMA_HOSTS.
    """
    # Reinitialize the factory to ensure a clean state before discovery
    LLMFactory.reinitialize()

    # The factory automatically runs discovery on initialization,
    # so we just need to check the results.
    
    # Use the public API to get discovered models for the Ollama runtime
    ollama_models_info = LLMFactory.list_models_by_runtime(LLMRuntime.OLLAMA)
    
    assert len(ollama_models_info) > 0, "No models were discovered from the configured Ollama host(s)."

    # Check that each registered model has correct runtime properties
    host_url = os.getenv("OLLAMA_HOSTS").split(',')[0].strip() # Check against the first configured host
    
    for model_info in ollama_models_info:
        assert model_info.runtime == LLMRuntime.OLLAMA.value
        assert model_info.host_url == host_url
        
        # Verify the model identifier format
        # e.g., llama3:latest:ollama@localhost:11434
        assert f":{LLMRuntime.OLLAMA.value}@" in model_info.model_identifier
        assert model_info.display_name in model_info.model_identifier

    # Reinitialize again to clean up for other test modules
    LLMFactory.reinitialize()
