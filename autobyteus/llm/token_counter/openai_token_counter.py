import tiktoken
from typing import List, TYPE_CHECKING
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import Message

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

class OpenAITokenCounter(BaseTokenCounter):
    """
    A token counter implementation for OpenAI models using tiktoken.
    """

    def __init__(self, model: LLMModel, llm: 'BaseLLM' = None):
        super().__init__(model, llm)
        try:
            self.encoding = tiktoken.encoding_for_model(model.value)
        except Exception:
            # fallback if model_name is not recognized
            self.encoding = tiktoken.get_encoding("cl100k_base")

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
            total_tokens += len(self.encoding.encode(processed_message))
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
        return len(self.encoding.encode(processed_message))

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
        return len(self.encoding.encode(text))
