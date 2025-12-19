import logging
import tiktoken
from typing import List, TYPE_CHECKING
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import Message

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

logger = logging.getLogger(__name__)

class OpenAITokenCounter(BaseTokenCounter):
    """
    A token counter implementation for OpenAI models using tiktoken.
    """

    def __init__(self, model: LLMModel, llm: 'BaseLLM' = None):
        super().__init__(model, llm)
        try:
            self.encoding = tiktoken.encoding_for_model(model.value)
        except Exception:
            # If the specific model is unknown, fall back to the widely available
            # cl100k_base encoding. tiktoken bundles this file; it loads locally
            # without needing network access.
            try:
                logger.warning(
                    "tiktoken encoding_for_model failed for '%s'; falling back to cl100k_base (approximate token counts).",
                    model.value,
                )
                self.encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # As a last resort (e.g., stripped-down wheels), degrade gracefully
                # with a naive whitespace encoder so tests can still execute offline.
                logger.warning(
                    "tiktoken cl100k_base unavailable; using whitespace token counting for model '%s' (very approximate).",
                    model.value,
                )
                self.encoding = None
        self._encode = self.encoding.encode if self.encoding else (lambda text: text.split() if text else [])

    def convert_to_internal_format(self, messages: List[Message]) -> List[str]:
        """
        Convert messages to the internal format required for token counting.

        Args:
            messages (List[Message]): The list of input messages.

        Returns:
            List[str]: The list of processed message strings.
        """
        processed_messages = []
        for message in messages:
            processed_message = f"<im_start>{message.role.value}\n{message.content}\n<im_end>"
            processed_messages.append(processed_message)
        return processed_messages

    def count_input_tokens(self, messages: List[Message]) -> int:
        """
        Count the total number of tokens in the list of input messages using tiktoken.

        Args:
            messages (List[Message]): The list of input messages.

        Returns:
            int: The total number of input tokens.
        """
        if not messages:
            return 0
        processed_messages = self.convert_to_internal_format(messages)
        total_tokens = 0
        for processed_message in processed_messages:
            total_tokens += len(self._encode(processed_message))
        return total_tokens

    def count_output_tokens(self, message: Message) -> int:
        """
        Count the number of tokens in the output message using tiktoken.

        Args:
            message (Message): The output message.

        Returns:
            int: The number of output tokens.
        """
        if not message.content:
            return 0
        processed_message = f"<im_start>{message.role.value}\n{message.content}\n<im_end>"
        return len(self._encode(processed_message))

    def count_tokens(self, text: str) -> int:
        """
        Helper method to count tokens in a single text string.

        Args:
            text (str): The text to count tokens for.

        Returns:
            int: The number of tokens.
        """
        if not text:
            return 0
        return len(self._encode(text))
