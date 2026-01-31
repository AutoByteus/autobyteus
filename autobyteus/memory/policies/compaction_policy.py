from dataclasses import dataclass


@dataclass
class CompactionPolicy:
    trigger_ratio: float = 0.8
    raw_tail_turns: int = 4
    max_item_chars: int = 2000
    safety_margin_tokens: int = 256

    def should_compact(self, prompt_tokens: int, input_budget: int) -> bool:
        if input_budget <= 0:
            return True
        if prompt_tokens >= input_budget:
            return True
        return prompt_tokens >= int(self.trigger_ratio * input_budget)
