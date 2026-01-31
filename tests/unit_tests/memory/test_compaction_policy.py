from autobyteus.memory.policies.compaction_policy import CompactionPolicy


def test_should_compact_triggers_at_ratio():
    policy = CompactionPolicy(trigger_ratio=0.8)
    assert policy.should_compact(prompt_tokens=81, input_budget=100) is True


def test_should_compact_triggers_at_budget_limit():
    policy = CompactionPolicy(trigger_ratio=0.8)
    assert policy.should_compact(prompt_tokens=100, input_budget=100) is True


def test_should_compact_false_below_ratio():
    policy = CompactionPolicy(trigger_ratio=0.8)
    assert policy.should_compact(prompt_tokens=50, input_budget=100) is False
