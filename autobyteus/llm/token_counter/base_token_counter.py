
import abc
from typing import Optional

from autobyteus.llm.utils.llm_config import LLMConfig

class BaseTokenCounter(abc.ABC):
    """
    Base abstract class for token counting strategy.
    Different providers have different token counting approaches.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.input_tokens = 0
        self.output_tokens = 0

    @abc.abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Return the number of tokens for the given text based on the provider's methodology.
        """
        pass

    def add_input_tokens(self, text: str) -> bool:
        """
        Adds the computed tokens for an input text.
        Returns True always since there is no token limit.
        """
        tokens = self.count_tokens(text)
        self.input_tokens += tokens
        return True

    def add_output_tokens(self, text: str) -> bool:
        """
        Adds the computed tokens for an output text.
        Returns True always since there is no token limit.
        """
        tokens = self.count_tokens(text)
        self.output_tokens += tokens
        return True

    def reset(self):
        """
        Resets the counter for both input and output tokens.
        """
        self.input_tokens = 0
        self.output_tokens = 0

    def get_total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
