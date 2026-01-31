import pytest
import os
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel, ModelInfo, LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig

# Ensure the factory is initialized before tests are generated
LLMFactory.ensure_initialized()
# Get all unique model identifiers for parametrization
_all_models = LLMFactory.list_available_models()
all_model_identifiers = [model.model_identifier for model in _all_models]
_model_info_by_id = {model.model_identifier: model for model in _all_models}


def _maybe_skip_missing_api_key(model_identifier: str) -> None:
    model_info = _model_info_by_id.get(model_identifier)
    if not model_info:
        return

    provider = model_info.provider
    if isinstance(provider, str):
        try:
            provider = LLMProvider(provider)
        except ValueError:
            return
    # Map providers to required API keys for instantiation.
    required_env = {
        LLMProvider.MINIMAX: "MINIMAX_API_KEY",
        LLMProvider.QWEN: "DASHSCOPE_API_KEY",
        LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
        LLMProvider.KIMI: "KIMI_API_KEY",
        LLMProvider.GROK: "GROK_API_KEY",
        LLMProvider.ZHIPU: "ZHIPU_API_KEY",
        LLMProvider.MISTRAL: "MISTRAL_API_KEY",
        LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
        LLMProvider.OPENAI: "OPENAI_API_KEY",
    }

    env_var = required_env.get(provider)
    if env_var and not os.getenv(env_var):
        pytest.skip(f"{env_var} not set for provider {provider}. Skipping {model_identifier}.")

def pytest_generate_tests(metafunc):
    """Hook to dynamically parametrize tests that require 'model_identifier'."""
    if "model_identifier" in metafunc.fixturenames:
        # Filter out models that may not be available in a standard CI environment
        # For local testing, all models will be tested.
        if os.getenv("CI"):
            # In CI, only test direct API models which are more likely to have keys
            models_to_test = [
                identifier for identifier in all_model_identifiers 
                if "@" not in identifier # A simple way to filter for non-runtime models
            ]
            if not models_to_test:
                pytest.skip("No API models available to test in CI environment.")
        else:
            models_to_test = all_model_identifiers
        
        metafunc.parametrize("model_identifier", models_to_test)


@pytest.fixture(scope="session")
def llm_factory():
    """Fixture to provide a shared instance of LLMFactory."""
    return LLMFactory()


def test_list_available_models(llm_factory):
    """Test that list_available_models() returns a non-empty list of valid ModelInfo objects."""
    models_info = llm_factory.list_available_models()
    assert isinstance(models_info, list), "list_available_models should return a list."
    
    # In a CI environment, we might not have runtime models, but we should have API models.
    assert len(models_info) > 0, "The models list should not be empty."

    for model_info in models_info:
        assert isinstance(model_info, ModelInfo), "Each item should be a ModelInfo object."
        assert isinstance(model_info.model_identifier, str) and model_info.model_identifier
        assert isinstance(model_info.display_name, str) and model_info.display_name
        assert isinstance(model_info.runtime, str) and model_info.runtime

        if model_info.runtime != LLMRuntime.API.value:
            assert isinstance(model_info.host_url, str) and model_info.host_url
            assert "@" in model_info.model_identifier


def test_create_llm_valid_models(llm_factory, model_identifier):
    """Test that create_llm() successfully creates instances for all registered model identifiers."""
    _maybe_skip_missing_api_key(model_identifier)
    llm_instance = llm_factory.create_llm(model_identifier)
    assert isinstance(llm_instance, BaseLLM), f"Instance for {model_identifier} should be a BaseLLM."
    assert llm_instance.model.model_identifier == model_identifier


def test_llm_initialization_with_custom_config(llm_factory, model_identifier):
    """Test that create_llm() correctly initializes an LLM with a custom configuration."""
    _maybe_skip_missing_api_key(model_identifier)
    custom_config = LLMConfig(temperature=0.99, max_tokens=1234)
    llm_instance = llm_factory.create_llm(model_identifier, llm_config=custom_config)
    
    # Assert that the custom values have been correctly merged into the instance's config
    assert llm_instance.config.temperature == 0.99, f"LLM for {model_identifier} should have custom temperature."
    assert llm_instance.config.max_tokens == 1234, f"LLM for {model_identifier} should have custom max_tokens."
    # Also check that a default value from the model's original config is still present
    assert llm_instance.model.default_config is not None


def test_create_llm_invalid_identifier(llm_factory):
    """Test that create_llm() raises a ValueError for an unsupported model identifier."""
    invalid_identifier = "unsupported_model_xyz:fake@localhost:1234"
    with pytest.raises(ValueError, match=f"Model with identifier '{invalid_identifier}' not found."):
        llm_factory.create_llm(invalid_identifier)


def test_create_llm_ambiguous_name(llm_factory):
    """Test that create_llm() raises a ValueError for an ambiguous (non-unique) model name."""
    # To test this, we need to manually register two models with the same name but different runtimes.
    LLMFactory.reinitialize() # Start with a clean slate
    
    # Register dummy runtime models with the same name (no exact identifier match).
    LLMFactory.register_model(
        LLMModel(
            name="dummy-model",
            value="dummy-model",
            provider=LLMProvider.OLLAMA,
            llm_class=BaseLLM,
            canonical_name="dummy",
            runtime=LLMRuntime.OLLAMA,
            host_url="http://localhost:11434",
        )
    )
    LLMFactory.register_model(
        LLMModel(
            name="dummy-model",
            value="dummy-model",
            provider=LLMProvider.LMSTUDIO,
            llm_class=BaseLLM,
            canonical_name="dummy",
            runtime=LLMRuntime.LMSTUDIO,
            host_url="http://localhost:1234",
        )
    )
    
    ambiguous_name = "dummy-model"
    with pytest.raises(ValueError, match=f"The model name '{ambiguous_name}' is ambiguous."):
        llm_factory.create_llm(ambiguous_name)

    # Clean up and reinitialize for other tests
    LLMFactory.reinitialize()
