import pytest
import os
from autobyteus.multimedia.autobyteus_provider import AutobyteusMultimediaModelProvider
from autobyteus.multimedia.multimedia_client_factory import MultimediaClientFactory
from autobyteus.multimedia.models import MultimediaModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.api.autobyteus_multimedia_client import AutobyteusMultimediaClient


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
    """     
    Fixture to reinitialize the factory before each test and clean up after.
    This ensures test isolation by resetting the singleton state.
    """
    MultimediaClientFactory.reinitialize()
    yield
    MultimediaClientFactory.reinitialize()


def test_successful_model_registration():
    """Test successful discovery and registration of multimedia models from a live Autobyteus server."""
    # The setup_teardown fixture has already run discovery via reinitialize().
    all_models = list(MultimediaModel)
    autobyteus_models = [m for m in all_models if m.runtime == MultimediaRuntime.AUTOBYTEUS]

    assert len(autobyteus_models) > 0, "No multimedia models were discovered from the Autobyteus server."
    
    # Basic validation of the first registered model
    model_info = autobyteus_models[0]
    assert model_info.model_identifier
    assert model_info.runtime == MultimediaRuntime.AUTOBYTEUS
    
    # Check that the underlying client class is correct by creating an instance
    client_instance = MultimediaClientFactory.create_multimedia_client(model_info.model_identifier)
    assert isinstance(client_instance, AutobyteusMultimediaClient)


def test_no_models_available_from_server(mocker):
    """Test handling when the server returns an empty list of models."""
    # Mock the sync client's response to return no models
    mocker.patch(
        'autobyteus_llm_client.client.AutobyteusClient.get_available_multimedia_models_sync',
        return_value={"models": []}
    )
    
    # Re-initialize the factory. This re-runs the discovery process with the mock in place.
    MultimediaClientFactory.reinitialize()
    
    # Verify no models for this runtime were registered. Built-in models might still exist.
    all_models = list(MultimediaModel)
    autobyteus_models = [m for m in all_models if m.runtime == MultimediaRuntime.AUTOBYTEUS]
    assert len(autobyteus_models) == 0


def test_preserve_existing_registrations_on_failure(monkeypatch):
    """Test that existing registrations are preserved when discovery fails."""
    # The setup_teardown fixture ensures a clean, initialized factory state.
    
    # Manually register a dummy model to simulate a pre-existing state
    dummy_model = MultimediaModel(
        name="dummy-multimedia-model",
        value="dummy-multimedia-model",
        provider=MultimediaProvider.OPENAI, # Provider doesn't matter for this test
        client_class=AutobyteusMultimediaClient,
        runtime=MultimediaRuntime.AUTOBYTEUS,
        host_url="http://dummy-host:1234"
    )
    MultimediaClientFactory.register_model(dummy_model)
    
    # Force discovery to fail by using an invalid URL
    monkeypatch.setenv('AUTOBYTEUS_LLM_SERVER_HOSTS', 'http://invalid-server:9999')
    
    # Re-run discovery directly from the provider. This should fail gracefully without clearing existing models.
    AutobyteusMultimediaModelProvider.discover_and_register()
    
    # Verify the dummy model remains. We check the internal dict to avoid triggering re-initialization.
    autobyteus_models = [
        m for m in MultimediaClientFactory._models_by_identifier.values() 
        if m.runtime == MultimediaRuntime.AUTOBYTEUS
    ]
    
    assert len(autobyteus_models) == 1
    assert autobyteus_models[0].model_identifier == dummy_model.model_identifier
