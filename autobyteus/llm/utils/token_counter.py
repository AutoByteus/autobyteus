from autobyteus.llm.utils.llm_config import LLMConfig


class TokenCounter:
    def __init__(self, config: LLMConfig, is_api_model: bool = True, tokenizer=None):
        self.config = config
        self.is_api_model = is_api_model
        self.input_tokens = 0
        self.output_tokens = 0
        self.token_limit = self.config.token_limit
        self.tokenizer = tokenizer

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def add_input_tokens(self, tokens: int) -> bool:
        if self.token_limit and self.get_total_tokens() + tokens > self.token_limit:
            return False
        self.input_tokens += tokens
        return True

    def add_output_tokens(self, tokens: int) -> bool:
        if self.token_limit and self.get_total_tokens() + tokens > self.token_limit:
            return False
        self.output_tokens += tokens
        return True

    def get_total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def reset(self):
        self.input_tokens = 0
        self.output_tokens = 0