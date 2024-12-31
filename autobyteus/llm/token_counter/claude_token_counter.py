
import anthropic
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel

class ClaudeTokenCounter(BaseTokenCounter):
    """
    A token counter implementation for Claude (Anthropic) using the official Anthropic Python SDK.
    """
    def __init__(self, model: LLMModel):
        super().__init__(model)
        # Initialize anthropic client
        self.client = anthropic.Client()

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text using Anthropic's token counter.
        
        Note: This token count is only accurate for older models like claude-2.1.
        For newer Claude models, this should be considered a very rough estimate.
        For exact token counts with newer models, rely on the `usage` property
        in the API response instead.

        Args:
            text (str): The text to count tokens for.

        Returns:
            int: An approximate count of tokens in the text.
        """
        if not text:
            return 0
        # The count_tokens method from the anthropic client expects a list
        return self.client.count_tokens([text])
