
import abc
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import Message

class BaseTokenCounter(abc.ABC):
    """
    Base abstract class for token counting strategy.
    Different providers have different token counting approaches.
    """

    def __init__(self, model: str, llm: 'BaseLLM' = None):
        """
        Initialize the BaseTokenCounter with the model.

        Args:
            model (str): The model to be used for token counting.
            llm (BaseLLM, optional): The LLM instance. Defaults to None.
        """
        self.model = model
        self.llm = llm

    @abc.abstractmethod
    def count_input_tokens(self, messages: List[Message]) -> int:
        """
        Return the total number of tokens for the given list of input messages based on the provider's methodology.

        Args:
            messages (List[Message]): The list of input messages.

        Returns:
            int: The total number of input tokens.
        """
        pass

    @abc.abstractmethod
    def count_output_tokens(self, message: Message) -> int:
        """
        Return the number of tokens for the given output message based on the provider's methodology.

        Args:
            message (Message): The output message.

        Returns:
            int: The number of output tokens.
        """
        pass

    def reset(self):
        """
        Resets any internal counters or state. This method can be overridden by subclasses if needed.
        """
        pass

    def get_total_tokens(self, input_tokens: int, output_tokens: int) -> int:
        """
        Returns the total tokens based on provided input and output token counts.

        Args:
            input_tokens (int): The number of input tokens.
            output_tokens (int): The number of output tokens.

        Returns:
            int: The total number of tokens.
        """
        return input_tokens + output_tokens
