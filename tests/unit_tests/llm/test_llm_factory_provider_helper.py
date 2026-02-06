import pytest

from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime


@pytest.fixture
def isolated_llm_registry():
    old_initialized = LLMFactory._initialized
    old_models_by_identifier = LLMFactory._models_by_identifier
    old_models_by_provider = LLMFactory._models_by_provider

    LLMFactory._initialized = True
    LLMFactory._models_by_identifier = {}
    LLMFactory._models_by_provider = {}
    try:
        yield
    finally:
        LLMFactory._initialized = old_initialized
        LLMFactory._models_by_identifier = old_models_by_identifier
        LLMFactory._models_by_provider = old_models_by_provider


def _register_api_model(name: str, provider: LLMProvider) -> None:
    LLMFactory.register_model(
        LLMModel(
            name=name,
            value=name,
            provider=provider,
            llm_class=BaseLLM,
            canonical_name=name,
        )
    )


def test_get_provider_by_exact_model_identifier(isolated_llm_registry):
    _register_api_model("test-model-a", LLMProvider.OPENAI)

    provider = LLMFactory.get_provider("test-model-a")

    assert provider == LLMProvider.OPENAI


def test_get_provider_by_unique_name_fallback(isolated_llm_registry):
    LLMFactory.register_model(
        LLMModel(
            name="runtime-model",
            value="runtime-model",
            provider=LLMProvider.LMSTUDIO,
            llm_class=BaseLLM,
            canonical_name="runtime-model",
            runtime=LLMRuntime.LMSTUDIO,
            host_url="http://localhost:1234",
        )
    )

    provider = LLMFactory.get_provider("runtime-model")

    assert provider == LLMProvider.LMSTUDIO


def test_get_provider_returns_none_when_not_found(isolated_llm_registry):
    provider = LLMFactory.get_provider("missing-model")
    assert provider is None


def test_get_provider_raises_on_ambiguous_name(isolated_llm_registry):
    LLMFactory.register_model(
        LLMModel(
            name="shared-name",
            value="shared-name",
            provider=LLMProvider.OLLAMA,
            llm_class=BaseLLM,
            canonical_name="shared-name",
            runtime=LLMRuntime.OLLAMA,
            host_url="http://localhost:11434",
        )
    )
    LLMFactory.register_model(
        LLMModel(
            name="shared-name",
            value="shared-name",
            provider=LLMProvider.LMSTUDIO,
            llm_class=BaseLLM,
            canonical_name="shared-name",
            runtime=LLMRuntime.LMSTUDIO,
            host_url="http://localhost:1234",
        )
    )

    with pytest.raises(ValueError, match="The model name 'shared-name' is ambiguous"):
        LLMFactory.get_provider("shared-name")
