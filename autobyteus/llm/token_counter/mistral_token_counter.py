
import logging
from typing import Optional
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer

logger = logging.getLogger(__name__)

class MistralTokenCounter(BaseTokenCounter):
    """
    A token counter implementation for Mistral-based models.
    """

    def __init__(self, model: LLMModel):
        """
        Initialize the token counter with a specific model.

        Args:
            model (LLMModel): The model configuration to use for token counting.
        """
        super().__init__(model)
        try:
            self.tokenizer = MistralTokenizer.from_model(model.name, strict=False)
        except KeyError as e:
            logger.warning(f"Unknown model name: {model.name}. Falling back to v7 tokenizer.")
            self.tokenizer = MistralTokenizer.v7()
        except Exception as e:
            logger.error(f"Error initializing tokenizer for model {model.name}: {e}")
            logger.warning("Falling back to v7 tokenizer")
            self.tokenizer = MistralTokenizer.v7()

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text using Mistral's tokenizer.

        Args:
            text (str): The text to count tokens for.

        Returns:
            int: The number of tokens in the text.
        """
        if not text:
            return 0

        try:
            tokens = self.tokenizer.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return 0
