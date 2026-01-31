import pytest
from unittest.mock import MagicMock, patch

from autobyteus.llm.api.lmstudio_llm import LMStudioLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig


def _build_model(host_url: str, runtime: LLMRuntime = LLMRuntime.LMSTUDIO) -> LLMModel:
    return LLMModel(
        name="lmstudio-test",
        value="lmstudio-test",
        provider=LLMProvider.LMSTUDIO,
        llm_class=LMStudioLLM,
        canonical_name="lmstudio-test",
        runtime=runtime,
        host_url=host_url,
    )


def test_lmstudio_llm_requires_host_url():
    model = _build_model(host_url=None, runtime=LLMRuntime.API)
    with pytest.raises(ValueError, match="host_url"):
        LMStudioLLM(model=model, llm_config=LLMConfig())


def test_lmstudio_llm_sets_base_url_and_api_key(monkeypatch):
    monkeypatch.setenv("LMSTUDIO_API_KEY", "test-key")
    model = _build_model(host_url="http://localhost:1234")

    with patch("autobyteus.llm.api.openai_compatible_llm.OpenAI") as openai_cls:
        openai_cls.return_value = MagicMock()
        llm = LMStudioLLM(model=model, llm_config=LLMConfig())

        assert llm.model is model
        openai_cls.assert_called_once()
        _, kwargs = openai_cls.call_args
        assert kwargs["base_url"] == "http://localhost:1234/v1"
        assert kwargs["api_key"] == "test-key"
