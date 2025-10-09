import pytest
import os
from autobyteus.llm.autobyteus_provider import AutobyteusModelProvider
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.models import LLMModel, LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.api.autobyteus_llm import AutobyteusLLM

@pytest.fixture(autouse=True)
def check_autobyteus_env():
    """
    Fixture to skip all tests in this module if the Autobyteus server is not configured.
    This runs automatically for each test.
    """
    #if not os.getenv("AUTOBYTEUS_LLM_SERVER_HOSTS") or not os.getenv("AUTOBYTEUS_API_KEY") or os.getenv("CI"):
    #    pytest.skip("Requires AUTOBYTEUS_LLM_SERVER_HOSTS and AUTOBYTEUS_API_KEY, and is skipped in CI.")


@pytest.fixture(autouse=True)
def setup_teardown():
    """Fixture to reinitialize the factory before each test and clean up after."""
    LLMFactory.reinitialize()
    yield
    LLMFactory.reinitialize()


def test_successful_model_registration():
    """Test successful discovery and registration of models from a live Autobyteus server."""
    # The factory initialization in the setup_teardown fixture already ran discovery.
    autobyteus_models = LLMFactory.list_models_by_runtime(LLMRuntime.AUTOBYTEUS)

    assert len(autobyteus_models) > 0, "No models were discovered from the Autobyteus server."
    
    # Basic validation of the first registered model
    model_info = autobyteus_models[0]
    assert model_info.model_identifier
    assert model_info.runtime == LLMRuntime.AUTOBYTEUS.value
    
    # Check that the underlying LLM class is correct by creating an instance
    llm_instance = LLMFactory.create_llm(model_info.model_identifier)
    assert isinstance(llm_instance, AutobyteusLLM)


def test_no_models_available_from_server(mocker):
    """Test handling when server returns an empty list of models."""
    # Mock the sync client's response to return no models
    mocker.patch(
        'autobyteus.clients.autobyteus_client.AutobyteusClient.get_available_llm_models_sync',
        return_value={"models": []}
    )
    
    # Re-run discovery
    AutobyteusModelProvider.discover_and_register()
    
    # Verify no models for this runtime were registered
    autobyteus_models = LLMFactory.list_models_by_runtime(LLMRuntime.AUTOBYTEUS)
    assert len(autobyteus_models) == 0


def test_preserve_existing_registrations_on_failure(monkeypatch):
    """Test that existing registrations are preserved when discovery fails."""
    # Manually register a dummy model to simulate a pre-existing state
    dummy_model = LLMModel(
        name="backup-model",
        value="backup-model",
        provider=LLMProvider.AUTOBYTEUS,
        llm_class=AutobyteusLLM,
        canonical_name="backup",
        runtime=LLMRuntime.AUTOBYTEUS,
        host_url="http://dummy-host:1234"
    )
    LLMFactory.register_model(dummy_model)
    
    # Force discovery to fail by using an invalid URL
    monkeypatch.setenv('AUTOBYTEUS_LLM_SERVER_HOSTS', 'http://invalid-server:9999')
    
    # Re-run discovery
    AutobyteusModelProvider.discover_and_register()
    
    # Verify the dummy model remains
    autobyteus_models = LLMFactory.list_models_by_runtime(LLMRuntime.AUTOBYTEUS)
    assert len(autobyteus_models) == 1
    assert autobyteus_models[0].model_identifier == dummy_model.model_identifier
