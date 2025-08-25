import pytest
import os
from autobyteus.multimedia.image.autobyteus_image_provider import AutobyteusImageModelProvider
from autobyteus.multimedia.image.image_client_factory import ImageClientFactory
from autobyteus.multimedia.image.image_model import ImageModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.image.api.autobyteus_image_client import AutobyteusImageClient


@pytest.fixture(autouse=True)
def check_autobyteus_env():
    """
    Fixture to skip all tests in this module if the Autobyteus server is not configured.
    """
    #if not os.getenv("AUTOBYTEUS_LLM_SERVER_HOSTS") or not os.getenv("AUTOBYTEUS_API_KEY") or os.getenv("CI"):
    #    pytest.skip("Requires AUTOBYTEUS_LLM_SERVER_HOSTS and AUTOBYTEUS_API_KEY, and is skipped in CI.")


@pytest.fixture(autouse=True)
def setup_teardown():
    """     
    Fixture to reinitialize the factory before each test and clean up after.
    """
    ImageClientFactory.reinitialize()
    yield
    ImageClientFactory.reinitialize()


def test_successful_model_registration():
    """Test successful discovery and registration of image models from a live Autobyteus server."""
    all_models = list(ImageModel)
    autobyteus_models = [m for m in all_models if m.runtime == MultimediaRuntime.AUTOBYTEUS]

    assert len(autobyteus_models) > 0, "No image models were discovered from the Autobyteus server."
    
    model_info = autobyteus_models[0]
    assert model_info.model_identifier
    assert model_info.runtime == MultimediaRuntime.AUTOBYTEUS
    
    client_instance = ImageClientFactory.create_image_client(model_info.model_identifier)
    assert isinstance(client_instance, AutobyteusImageClient)


def test_no_models_available_from_server(mocker):
    """Test handling when the server returns an empty list of models."""
    mocker.patch(
        'autobyteus_llm_client.client.AutobyteusClient.get_available_multimedia_models_sync',
        return_value={"models": []}
    )
    
    ImageClientFactory.reinitialize()
    
    all_models = list(ImageModel)
    autobyteus_models = [m for m in all_models if m.runtime == MultimediaRuntime.AUTOBYTEUS]
    assert len(autobyteus_models) == 0


def test_preserve_existing_registrations_on_failure(monkeypatch):
    """Test that existing registrations are preserved when discovery fails."""
    dummy_model = ImageModel(
        name="dummy-image-model",
        value="dummy-image-model",
        provider=MultimediaProvider.OPENAI,
        client_class=AutobyteusImageClient, # Class doesn't matter, just needs to be valid
        runtime=MultimediaRuntime.AUTOBYTEUS,
        host_url="http://dummy-host:1234"
    )
    ImageClientFactory.register_model(dummy_model)
    
    monkeypatch.setenv('AUTOBYTEUS_LLM_SERVER_HOSTS', 'http://invalid-server:9999')
    
    AutobyteusImageModelProvider.discover_and_register()
    
    autobyteus_models = [
        m for m in ImageClientFactory._models_by_identifier.values() 
        if m.runtime == MultimediaRuntime.AUTOBYTEUS
    ]
    
    assert len(autobyteus_models) == 1
    assert autobyteus_models[0].model_identifier == dummy_model.model_identifier
