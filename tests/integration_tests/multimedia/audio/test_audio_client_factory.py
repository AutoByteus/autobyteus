import pytest
from autobyteus.multimedia.audio.audio_client_factory import AudioClientFactory
from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
from autobyteus.multimedia.audio.audio_model import AudioModel
from autobyteus.multimedia.runtimes import MultimediaRuntime

# Ensure the factory is initialized before tests are generated
AudioClientFactory.ensure_initialized()
all_model_identifiers = [model.model_identifier for model in list(AudioModel)]

def pytest_generate_tests(metafunc):
    """Hook to dynamically parametrize tests."""
    if "model_identifier" in metafunc.fixturenames:
        metafunc.parametrize("model_identifier", all_model_identifiers)

@pytest.fixture(scope="session")
def audio_client_factory():
    """Fixture to provide a shared instance of AudioClientFactory."""
    return AudioClientFactory()

def test_list_available_models(audio_client_factory):
    """Test that iterating AudioModel returns a non-empty list of valid objects."""
    all_models = list(AudioModel)
    assert isinstance(all_models, list)
    assert len(all_models) > 0

    for model in all_models:
        assert isinstance(model, AudioModel)
        assert isinstance(model.model_identifier, str) and model.model_identifier
        assert isinstance(model.runtime, MultimediaRuntime)

def test_create_audio_client_valid_models(audio_client_factory, model_identifier):
    """Test that create_audio_client() successfully creates instances for all registered models."""
    client_instance = audio_client_factory.create_audio_client(model_identifier)
    assert isinstance(client_instance, BaseAudioClient)
    assert client_instance.model.model_identifier == model_identifier

def test_create_audio_client_invalid_identifier(audio_client_factory):
    """Test that create_audio_client() raises a ValueError for an unsupported model identifier."""
    invalid_identifier = "unsupported-audio-model-xyz"
    with pytest.raises(ValueError, match=f"No audio model registered with the name '{invalid_identifier}'."):
        audio_client_factory.create_audio_client(invalid_identifier)
