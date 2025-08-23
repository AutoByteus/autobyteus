import pytest
import os
from autobyteus.multimedia.multimedia_client_factory import MultimediaClientFactory
from autobyteus.multimedia.base_multimedia_client import BaseMultimediaClient
from autobyteus.multimedia.models import MultimediaModel
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

# Ensure the factory is initialized before tests are generated
MultimediaClientFactory.ensure_initialized()
# Get all unique model identifiers for parametrization
all_model_identifiers = [model.model_identifier for model in list(MultimediaModel)]

def pytest_generate_tests(metafunc):
    """Hook to dynamically parametrize tests that require 'model_identifier'."""
    if "model_identifier" in metafunc.fixturenames:
        if os.getenv("CI"):
            # In CI, only test direct API models which are more likely to have keys set
            models_to_test = [
                identifier for identifier in all_model_identifiers 
                if "@" not in identifier # A simple way to filter for non-runtime models
            ]
            if not models_to_test:
                pytest.skip("No API-based multimedia models available to test in CI environment.")
        else:
            models_to_test = all_model_identifiers
        
        metafunc.parametrize("model_identifier", models_to_test)


@pytest.fixture(scope="session")
def multimedia_client_factory():
    """Fixture to provide a shared instance of MultimediaClientFactory."""
    return MultimediaClientFactory()


def test_list_available_models(multimedia_client_factory):
    """Test that iterating MultimediaModel returns a non-empty list of valid objects."""
    all_models = list(MultimediaModel)
    assert isinstance(all_models, list), "Iterating MultimediaModel should produce a list."
    
    # In a CI environment, we might not have runtime models, but we should have API models.
    assert len(all_models) > 0, "The models list should not be empty."

    for model in all_models:
        assert isinstance(model, MultimediaModel), "Each item should be a MultimediaModel object."
        assert isinstance(model.model_identifier, str) and model.model_identifier
        assert isinstance(model.name, str) and model.name
        assert isinstance(model.runtime, MultimediaRuntime)

        if model.runtime != MultimediaRuntime.API:
            assert isinstance(model.host_url, str) and model.host_url
            assert "@" in model.model_identifier


def test_create_multimedia_client_valid_models(multimedia_client_factory, model_identifier):
    """Test that create_multimedia_client() successfully creates instances for all registered models."""
    client_instance = multimedia_client_factory.create_multimedia_client(model_identifier)
    assert isinstance(client_instance, BaseMultimediaClient), f"Instance for {model_identifier} should be a BaseMultimediaClient."
    assert client_instance.model.model_identifier == model_identifier


def test_client_initialization_with_custom_config(multimedia_client_factory, model_identifier):
    """Test that create_multimedia_client() correctly initializes a client with a custom configuration."""
    custom_config_params = {"n": 5, "size": "512x512", "quality": "hd", "style": "natural"}
    custom_config = MultimediaConfig(params=custom_config_params)
    
    client_instance = multimedia_client_factory.create_multimedia_client(model_identifier, config_override=custom_config)
    
    # Assert that the custom values have been correctly merged into the instance's config
    final_params = client_instance.config.params
    assert final_params["n"] == 5
    assert final_params["size"] == "512x512"
    assert final_params["quality"] == "hd"
    assert final_params["style"] == "natural"
    
    # Also check that the model's original default config object is still there
    assert client_instance.model.default_config is not None


def test_create_multimedia_client_invalid_identifier(multimedia_client_factory):
    """Test that create_multimedia_client() raises a ValueError for an unsupported model identifier."""
    invalid_identifier = "unsupported-image-model-xyz@fake-host:1234"
    with pytest.raises(ValueError, match=f"No multimedia model registered with the name '{invalid_identifier}'."):
        multimedia_client_factory.create_multimedia_client(invalid_identifier)
