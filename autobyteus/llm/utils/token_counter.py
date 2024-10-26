import tiktoken

class TokenCounter:
    def __init__(self, config=None):
        self.token_limit = getattr(config, 'token_limit', None)
        self.model_name = getattr(config, 'model_name', None)
        if self.token_limit and self.model_name:
            self.encoding = tiktoken.encoding_for_model(self.model_name)
        else:
            self.encoding = None
        self.input_tokens = 0
        self.output_tokens = 0

    def count_tokens(self, text: str) -> int:
        if not self.encoding:
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
