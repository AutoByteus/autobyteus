# file: autobyteus/tests/unit_tests/llm/api/test_zhipu_thinking_config.py
"""
Unit tests for Zhipu thinking config normalization.
"""
import pytest

from autobyteus.llm.api.zhipu_llm import ZhipuLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig


def test_zhipu_normalizes_thinking_params(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

    llm = ZhipuLLM(
        model=LLMModel["glm-4.7"],
        llm_config=LLMConfig(extra_params={
            "thinking_type": "enabled",
        })
    )

    thinking = llm.config.extra_params["thinking"]
    assert thinking["type"] == "enabled"


def test_zhipu_preserves_existing_extra_body(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")

    llm = ZhipuLLM(
        model=LLMModel["glm-4.7"],
        llm_config=LLMConfig(extra_params={
            "thinking": {"type": "disabled"},
            "thinking_type": "disabled",
        })
    )

    thinking = llm.config.extra_params["thinking"]
    assert thinking["type"] == "disabled"
