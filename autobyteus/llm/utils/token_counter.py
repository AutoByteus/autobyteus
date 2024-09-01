import tiktoken
from autobyteus.llm.utils.llm_config import LLMConfig

class TokenCounter:
    def __init__(self, config: LLMConfig):
        self.token_limit = config.token_limit
        self.model_name = config.model_name
        if self.token_limit:
            self.encoding = tiktoken.encoding_for_model(self.model_name)
        self.input_tokens = 0
        self.output_tokens = 0

    def count_tokens(self, text: str) -> int:
        if not self.token_limit:
            return 0
        return len(self.encoding.encode(text))

    def add_input_tokens(self, text: str) -> bool:
        tokens = self.count_tokens(text)
        if self.token_limit and self.input_tokens + self.output_tokens + tokens > self.token_limit:
            return False
        self.input_tokens += tokens
        return True

    def add_output_tokens(self, text: str) -> bool:
        tokens = self.count_tokens(text)
        if self.token_limit and self.input_tokens + self.output_tokens + tokens > self.token_limit:
            return False
        self.output_tokens += tokens
        return True

    def reset(self):
        self.input_tokens = 0
        self.output_tokens = 0

    def get_total_tokens(self):
        return self.input_tokens + self.output_tokens