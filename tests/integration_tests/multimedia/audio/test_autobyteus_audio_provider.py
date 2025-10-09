import pytest
import os
from autobyteus.multimedia.audio.autobyteus_audio_provider import AutobyteusAudioModelProvider
from autobyteus.multimedia.audio.audio_client_factory import AudioClientFactory
from autobyteus.multimedia.audio.audio_model import AudioModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.audio.api.autobyteus_audio_client import AutobyteusAudioClient


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
    AudioClientFactory.reinitialize()
    yield
    AudioClientFactory.reinitialize()


def test_successful_model_registration():
    """Test successful discovery and registration of audio models from a live Autobyteus server."""
    all_models = list(AudioModel)
    autobyteus_models = [m for m in all_models if m.runtime == MultimediaRuntime.AUTOBYTEUS]

    assert len(autobyteus_models) > 0, "No audio models were discovered from the Autobyteus server."
    
    model_info = autobyteus_models[0]
    assert model_info.model_identifier
    assert model_info.runtime == MultimediaRuntime.AUTOBYTEUS
    
    client_instance = AudioClientFactory.create_audio_client(model_info.model_identifier)
    assert isinstance(client_instance, AutobyteusAudioClient)


def test_no_models_available_from_server(mocker):
    """Test handling when the server returns an empty list of models."""
    mocker.patch(
        'autobyteus.clients.autobyteus_client.AutobyteusClient.get_available_audio_models_sync',
        return_value={"models": []}
    )
    
    AudioClientFactory.reinitialize()
    
    all_models = list(AudioModel)
    autobyteus_models = [m for m in all_models if m.runtime == MultimediaRuntime.AUTOBYTEUS]
    assert len(autobyteus_models) == 0


def test_preserve_existing_registrations_on_failure(monkeypatch):
    """Test that existing registrations are preserved when discovery fails."""
    dummy_model = AudioModel(
        name="dummy-audio-model",
        value="dummy-audio-model",
        provider=MultimediaProvider.GOOGLE,
        client_class=AutobyteusAudioClient, # Class doesn't matter, just needs to be valid
        runtime=MultimediaRuntime.AUTOBYTEUS,
        host_url="http://dummy-host:1234"
    )
    AudioClientFactory.register_model(dummy_model)
    
    monkeypatch.setenv('AUTOBYTEUS_LLM_SERVER_HOSTS', 'http://invalid-server:9999')
    
    AutobyteusAudioModelProvider.discover_and_register()
    
    autobyteus_models = [
        m for m in AudioClientFactory._models_by_identifier.values() 
        if m.runtime == MultimediaRuntime.AUTOBYTEUS
    ]
    
    assert len(autobyteus_models) == 1
    assert autobyteus_models[0].model_identifier == dummy_model.model_identifier
