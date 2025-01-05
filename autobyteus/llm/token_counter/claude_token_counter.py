
import anthropic
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import Message
from typing import List

class ClaudeTokenCounter(BaseTokenCounter):
    """
    A token counter implementation for Claude (Anthropic) using the official Anthropic Python SDK.
    """

    def __init__(self, model: LLMModel):
        super().__init__(model)
        # Initialize anthropic client
        self.client = anthropic.Client()

    def count_input_tokens(self, messages: List[Message]) -> int:
        """
        Count the total number of tokens in the list of input messages using Anthropic's token counter.

        Args:
            messages (List[Message]): The list of input messages.

        Returns:
            int: The total number of input tokens.
        """
        if not messages:
            return 0
        texts = [message.content for message in messages]
        return self.client.count_tokens(texts)

    def count_output_tokens(self, message: Message) -> int:
        """
        Count the number of tokens in the output message using Anthropic's token counter.

        Args:
            message (Message): The output message.

        Returns:
            int: The number of output tokens.
        """
        if not message.content:
            return 0
        return self.client.count_tokens([message.content])
