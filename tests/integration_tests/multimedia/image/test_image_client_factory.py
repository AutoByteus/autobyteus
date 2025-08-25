import pytest
import os
from autobyteus.multimedia.image.image_client_factory import ImageClientFactory
from autobyteus.multimedia.image.base_image_client import BaseImageClient
from autobyteus.multimedia.image.image_model import ImageModel
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

# Ensure the factory is initialized before tests are generated
ImageClientFactory.ensure_initialized()
# Get all unique model identifiers for parametrization
all_model_identifiers = [model.model_identifier for model in list(ImageModel)]

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
                pytest.skip("No API-based image models available to test in CI environment.")
        else:
            models_to_test = all_model_identifiers
        
        metafunc.parametrize("model_identifier", models_to_test)


@pytest.fixture(scope="session")
def image_client_factory():
    """Fixture to provide a shared instance of ImageClientFactory."""
    return ImageClientFactory()


def test_list_available_models(image_client_factory):
    """Test that iterating ImageModel returns a non-empty list of valid objects."""
    all_models = list(ImageModel)
    assert isinstance(all_models, list)
    assert len(all_models) > 0

    for model in all_models:
        assert isinstance(model, ImageModel)
        assert isinstance(model.model_identifier, str) and model.model_identifier
        assert isinstance(model.runtime, MultimediaRuntime)

        if model.runtime != MultimediaRuntime.API:
            assert isinstance(model.host_url, str) and model.host_url
            assert "@" in model.model_identifier


def test_create_image_client_valid_models(image_client_factory, model_identifier):
    """Test that create_image_client() successfully creates instances for all registered models."""
    client_instance = image_client_factory.create_image_client(model_identifier)
    assert isinstance(client_instance, BaseImageClient)
    assert client_instance.model.model_identifier == model_identifier


def test_client_initialization_with_custom_config(image_client_factory, model_identifier):
    """Test that create_image_client() correctly initializes a client with a custom configuration."""
    custom_config_params = {"n": 5, "size": "512x512"}
    custom_config = MultimediaConfig(params=custom_config_params)
    
    client_instance = image_client_factory.create_image_client(model_identifier, config_override=custom_config)
    
    final_params = client_instance.config.params
    assert final_params["n"] == 5
    assert final_params["size"] == "512x512"
    assert client_instance.model.default_config is not None


def test_create_image_client_invalid_identifier(image_client_factory):
    """Test that create_image_client() raises a ValueError for an unsupported model identifier."""
    invalid_identifier = "unsupported-image-model-xyz@fake-host:1234"
    with pytest.raises(ValueError, match=f"No image model registered with the name '{invalid_identifier}'."):
        image_client_factory.create_image_client(invalid_identifier)
