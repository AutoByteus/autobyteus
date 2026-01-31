import pytest
from unittest.mock import MagicMock

from autobyteus.agent.token_budget import resolve_token_budget, TokenBudget
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.memory.policies.compaction_policy import CompactionPolicy


def test_resolve_budget_prefers_model_context():
    model = MagicMock(
        max_context_tokens=12000,
        default_compaction_ratio=0.8,
        default_safety_margin_tokens=256,
    )
    config = LLMConfig(max_tokens=1000)
    policy = CompactionPolicy()

    budget = resolve_token_budget(model, config, policy)

    assert isinstance(budget, TokenBudget)
    assert budget.max_context_tokens == 12000
    assert budget.max_output_tokens == 1000
    assert budget.safety_margin_tokens == 256
    assert budget.compaction_ratio == 0.8
    assert budget.input_budget == 12000 - 1000 - 256


def test_resolve_budget_uses_config_overrides():
    model = MagicMock(
        max_context_tokens=8000,
        default_compaction_ratio=0.8,
        default_safety_margin_tokens=256,
    )
    config = LLMConfig(
        max_tokens=500,
        compaction_ratio=0.5,
        safety_margin_tokens=128,
    )
    policy = CompactionPolicy(trigger_ratio=0.9, safety_margin_tokens=512)

    budget = resolve_token_budget(model, config, policy)

    assert budget.compaction_ratio == 0.5
    assert budget.safety_margin_tokens == 128
    assert budget.input_budget == 8000 - 500 - 128


def test_resolve_budget_falls_back_to_config_token_limit():
    model = MagicMock(
        max_context_tokens=None,
        default_compaction_ratio=None,
        default_safety_margin_tokens=None,
    )
    config = LLMConfig(token_limit=6000, max_tokens=500)
    policy = CompactionPolicy(trigger_ratio=0.7, safety_margin_tokens=200)

    budget = resolve_token_budget(model, config, policy)

    assert budget.max_context_tokens == 6000
    assert budget.compaction_ratio == 0.7
    assert budget.safety_margin_tokens == 200
    assert budget.input_budget == 6000 - 500 - 200


def test_resolve_budget_returns_none_without_context_limits():
    model = MagicMock(
        max_context_tokens=None,
        default_compaction_ratio=None,
        default_safety_margin_tokens=None,
    )
    config = LLMConfig()
    policy = CompactionPolicy()

    budget = resolve_token_budget(model, config, policy)

    assert budget is None
