
import logging
from typing import List, TYPE_CHECKING
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from mistral_common.protocol.instruct.messages import UserMessage, AssistantMessage, SystemMessage
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from autobyteus.llm.utils.messages import Message, MessageRole

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

logger = logging.getLogger(__name__)

class MistralTokenCounter(BaseTokenCounter):
    """
    A token counter implementation for Mistral-based models.
    """

    def __init__(self, model: LLMModel, llm: 'BaseLLM' = None):
        """
        Initialize the token counter with a specific model.

        Args:
            model (LLMModel): The model configuration to use for token counting.
            llm (BaseLLM, optional): The LLM instance. Defaults to None.
        """
        super().__init__(model, llm)
        try:
            self.tokenizer = MistralTokenizer.from_model(model.value, strict=False)
        except KeyError:
            logger.warning(f"Unknown model value: {model.value}. Falling back to v7 tokenizer.")
            self.tokenizer = MistralTokenizer.v7()
        except Exception as e:
            logger.error(f"Error initializing tokenizer for model {model.value}: {e}")
            logger.warning("Falling back to v7 tokenizer")
            self.tokenizer = MistralTokenizer.v7()

    def _convert_to_mistral_common_message(self, message: Message, is_last: bool = False):
        """
        Convert our Message type to Mistral Common message type.
        
        Args:
            message (Message): The message to convert.
            is_last (bool): Whether this is the last message in the sequence.
            
        Returns:
            Union[UserMessage, AssistantMessage, SystemMessage]: The converted message.
            
        Raises:
            ValueError: If the message role is not supported.
        """
        if message.role == MessageRole.USER:
            return UserMessage(content=message.content)
        elif message.role == MessageRole.ASSISTANT:
            # For assistant messages, set prefix=True if this is the last message
            return AssistantMessage(content=str(message.content), prefix=is_last)
        elif message.role == MessageRole.SYSTEM:
            return SystemMessage(content=str(message.content))
        raise ValueError(f"Unsupported message role: {message.role}")

    def count_input_tokens(self, messages: List[Message]) -> int:
        """
        Count the total number of tokens in the list of input messages using Mistral's tokenizer.

        Args:
            messages (List[Message]): The list of input messages.

        Returns:
            int: The total number of input tokens.

        Raises:
            Exception: If token counting fails for any reason.
        """
        if not messages:
            return 0
            
        # Convert messages to Mistral Common message format with proper last message handling
        mistral_messages = [
            self._convert_to_mistral_common_message(message, is_last=(i == len(messages) - 1))
            for i, message in enumerate(messages)
        ]
        
        # Construct a single ChatCompletionRequest with all messages
        chat_request = ChatCompletionRequest(
            messages=mistral_messages,
            model=self.model.value
        )
        
        # Tokenize the entire request
        tokenized = self.tokenizer.encode_chat_completion(chat_request)
        return len(tokenized.tokens)

    def count_output_tokens(self, message: Message) -> int:
        """
        Count the number of tokens in the output message using Mistral's tokenizer.
        This implementation subtracts the token count of previous messages from the total tokens to isolate the output tokens.

        Args:
            message (Message): The output message.

        Returns:
            int: The number of output tokens.

        Raises:
            Exception: If token counting fails for any reason.
        """
        # Calculate total tokens for all messages including the assistant message
        all_tokens = self.count_input_tokens(self.llm.messages)
        # Exclude the last message (assistant message) to get previous messages
        prev_messages = self.llm.messages[:-1] if len(self.llm.messages) > 1 else []
        prev_tokens = self.count_input_tokens(prev_messages) if prev_messages else 0
        # The difference should correspond to the tokens for the assistant's last message
        return all_tokens - prev_tokens
