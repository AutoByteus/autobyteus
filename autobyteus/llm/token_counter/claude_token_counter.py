import anthropic
from typing import List, TYPE_CHECKING
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import Message

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

class ClaudeTokenCounter(BaseTokenCounter):
    """
    A token counter implementation for Claude (Anthropic) using the official Anthropic Python SDK.
    """

    def __init__(self, model: LLMModel, llm: 'BaseLLM' = None):
        super().__init__(model, llm)
        self.client = anthropic.Client()

    def convert_to_internal_format(self, messages: List[Message]) -> List[str]:
        """
        Convert messages to the internal format required for Claude token counting.

        Args:
            messages (List[Message]): The list of input messages.

        Returns:
            List[str]: The list of processed message strings.
        """
        processed_messages = []
        for message in messages:
            processed_message = f"{message.role.value}: {message.content}"
            processed_messages.append(processed_message)
        return processed_messages

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

        total_tokens = 0
        processed_messages = self.convert_to_internal_format(messages)
        
        for message in processed_messages:
            try:
                tokens = self.client.count_tokens(message)
                total_tokens += tokens
            except Exception as e:
                raise ValueError(f"Failed to count tokens for message: {str(e)}")
                
        return total_tokens

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
            
        try:
            processed_message = f"{message.role.value}: {message.content}"
            return self.client.count_tokens(processed_message)
        except Exception as e:
            raise ValueError(f"Failed to count output tokens: {str(e)}")
