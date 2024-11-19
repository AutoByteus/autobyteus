import tiktoken

class TokenCounter:
    def __init__(self, config=None, is_api_model=True):
        self.token_limit = getattr(config, 'token_limit', None)
        self.model_name = getattr(config, 'model_name', None)
        self.is_api_model = is_api_model
        
        if self.is_api_model and self.model_name:
            try:
                self.encoding = tiktoken.encoding_for_model(self.model_name)
            except KeyError:
                # Fallback to default encoding if model-specific encoding is not found
                self.encoding = tiktoken.get_encoding("cl100k_base")
        else:
            self.encoding = None
            
        self.input_tokens = 0
        self.output_tokens = 0

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in the given text.
        Returns 0 for non-API models.
        """
        if not self.is_api_model or not self.encoding:
            return 0
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # Fallback to approximate token count if encoding fails
            return len(text.split())

    def add_input_tokens(self, tokens: int) -> bool:
        """
        Add input tokens to the counter.
        Returns True if successful, False if token limit would be exceeded.
        Always returns True for non-API models.
        """
        if not self.is_api_model:
            return True
            
        if self.token_limit and self.input_tokens + self.output_tokens + tokens > self.token_limit:
            return False
        self.input_tokens += tokens
        return True

    def add_output_tokens(self, tokens: int) -> bool:
        """
        Add output tokens to the counter.
        Returns True if successful, False if token limit would be exceeded.
        Always returns True for non-API models.
        """
        if not self.is_api_model:
            return True
            
        if self.token_limit and self.input_tokens + self.output_tokens + tokens > self.token_limit:
            return False
        self.output_tokens += tokens
        return True

    def reset(self):
        """Reset all token counters to zero."""
        self.input_tokens = 0
        self.output_tokens = 0

    def get_total_tokens(self):
        """Get the total number of tokens used (input + output)."""
        return self.input_tokens + self.output_tokens