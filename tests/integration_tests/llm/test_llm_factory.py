import pytest
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

@pytest.fixture(scope="module")
def llm_factory():
    """
    Fixture to provide an instance of LLMFactory.
    """
    return LLMFactory()

@pytest.fixture(scope="module")
def models(llm_factory):
    """
    Fixture to retrieve all models from the LLMFactory.
    """
    return llm_factory.get_all_models()

def test_get_all_models(llm_factory):
    """
    Test that LLMFactory.get_all_models() returns a non-empty list of models.
    """
    models = llm_factory.get_all_models()
    assert isinstance(models, list), "get_all_models should return a list."
    assert len(models) > 0, "The models list should not be empty."

def test_create_llm_valid_models(llm_factory, model_name):
    """
    Test that LLMFactory.create_llm() successfully creates instances for all registered models.
    """
    llm_instance = llm_factory.create_llm(model_name)
    assert isinstance(llm_instance, BaseLLM), f"Instance for {model_name} should be a BaseLLM."

def test_llm_initialization_with_custom_config(llm_factory, model_name):
    """
    Test that LLMFactory.create_llm() correctly initializes an LLM with a custom configuration.
    """
    custom_config = LLMConfig(rate_limit=40, token_limit=8192)  # Replace with actual configuration parameters
    llm_instance = llm_factory.create_llm(model_name, custom_config=custom_config)
    assert llm_instance.config == custom_config, f"LLM instance for {model_name} should have the custom config."

def pytest_generate_tests(metafunc):
    """
    Hook to dynamically parametrize tests that require 'model_name'.
    """
    if "model_name" in metafunc.fixturenames:
        llm_factory = LLMFactory()
        models = llm_factory.get_all_models()
        metafunc.parametrize("model_name", models)

def test_create_llm_invalid_model(llm_factory):
    """
    Test that LLMFactory.create_llm() raises a ValueError when an unsupported model is requested.
    """
    invalid_model = "unsupported_model_xyz"
    with pytest.raises(ValueError) as exc_info:
        llm_factory.create_llm(invalid_model)
    assert str(exc_info.value) == f"Unsupported model: {invalid_model}"

def test_plugins_registration(llm_factory):
    """
    Test that plugins are discovered and registered correctly in the LLMFactory registry.
    """
    # This test assumes that there are plugins that add models to the registry.
    # Replace 'plugin_added_model' with actual model names added by plugins.
    plugin_added_models = ["plugin_model_1", "plugin_model_2"]  # Example model names
    models = llm_factory.get_all_models()
    for plugin_model in plugin_added_models:
        assert plugin_model in models, f"Plugin model {plugin_model} should be registered in the factory."
