
import logging
from typing import List
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from mistral_common.protocol.instruct.messages import UserMessage, AssistantMessage, SystemMessage
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from autobyteus.llm.utils.messages import Message, MessageRole

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
        except KeyError:
            logger.warning(f"Unknown model name: {model.name}. Falling back to v7 tokenizer.")
            self.tokenizer = MistralTokenizer.v7()
        except Exception as e:
            logger.error(f"Error initializing tokenizer for model {model.name}: {e}")
            logger.warning("Falling back to v7 tokenizer")
            self.tokenizer = MistralTokenizer.v7()

    def _convert_to_mistral_common_message(self, message: Message):
        """
        Convert our Message type to Mistral Common message type.
        
        Args:
            message (Message): The message to convert.
            
        Returns:
            Union[UserMessage, AssistantMessage, SystemMessage]: The converted message.
            
        Raises:
            ValueError: If the message role is not supported.
        """
        if message.role == MessageRole.USER:
            return UserMessage(content=message.content)
        elif message.role == MessageRole.ASSISTANT:
            return AssistantMessage(content=str(message.content))
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
            
        # Convert messages to Mistral Common message format
        mistral_messages = [self._convert_to_mistral_common_message(message) for message in messages]
        
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

        Args:
            message (Message): The output message.

        Returns:
            int: The number of output tokens.

        Raises:
            Exception: If token counting fails for any reason.
        """
        if not message.content:
            return 0
            
        mistral_message = self._convert_to_mistral_common_message(message)
        chat_request = ChatCompletionRequest(
            messages=[mistral_message],
            model=self.model.value
        )
        tokenized = self.tokenizer.encode_chat_completion(chat_request)
        return len(tokenized.tokens)
