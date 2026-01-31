from dataclasses import dataclass
from typing import Optional

from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.memory.policies.compaction_policy import CompactionPolicy


@dataclass(frozen=True)
class TokenBudget:
    max_context_tokens: int
    max_output_tokens: int
    safety_margin_tokens: int
    compaction_ratio: float
    input_budget: int


def resolve_token_budget(
    model: LLMModel,
    config: LLMConfig,
    policy: CompactionPolicy,
) -> Optional[TokenBudget]:
    max_context_tokens = model.max_context_tokens or config.token_limit
    if not max_context_tokens:
        return None

    max_output_tokens = config.max_tokens or 0

    if config.safety_margin_tokens is not None:
        safety_margin = config.safety_margin_tokens
    elif model.default_safety_margin_tokens is not None:
        safety_margin = model.default_safety_margin_tokens
    else:
        safety_margin = policy.safety_margin_tokens

    if config.compaction_ratio is not None:
        compaction_ratio = config.compaction_ratio
    elif model.default_compaction_ratio is not None:
        compaction_ratio = model.default_compaction_ratio
    else:
        compaction_ratio = policy.trigger_ratio

    input_budget = max(0, max_context_tokens - max_output_tokens - safety_margin)

    return TokenBudget(
        max_context_tokens=max_context_tokens,
        max_output_tokens=max_output_tokens,
        safety_margin_tokens=safety_margin,
        compaction_ratio=compaction_ratio,
        input_budget=input_budget,
    )


def apply_compaction_policy(policy: CompactionPolicy, budget: TokenBudget) -> None:
    policy.trigger_ratio = budget.compaction_ratio
    policy.safety_margin_tokens = budget.safety_margin_tokens
