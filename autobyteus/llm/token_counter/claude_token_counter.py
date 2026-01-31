import anthropic
import json
from typing import List, TYPE_CHECKING, Dict, Any, Optional, Tuple
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import Message, MessageRole

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

class ClaudeTokenCounter(BaseTokenCounter):
    """
    A token counter implementation for Claude (Anthropic) using the official Anthropic Python SDK.
    """

    def __init__(self, model: LLMModel, llm: 'BaseLLM' = None):
        super().__init__(model, llm)
        self.client = anthropic.Anthropic()

    def convert_to_anthropic_messages(self, messages: List[Message]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Convert messages to the format required for Claude token counting.

        Args:
            messages (List[Message]): The list of input messages.

        Returns:
            Tuple[Optional[str], List[Dict[str, Any]]]: System prompt (if any) and message payloads.
        """
        system_parts: List[str] = []
        processed_messages: List[Dict[str, Any]] = []
        for message in messages:
            content = self._extract_message_text(message)
            if message.role == MessageRole.SYSTEM:
                system_parts.append(content)
                continue
            role = "assistant" if message.role == MessageRole.ASSISTANT else "user"
            processed_messages.append({"role": role, "content": content})
        system = "\n".join(system_parts) if system_parts else None
        return system, processed_messages

    def _extract_message_text(self, message: Message) -> str:
        if message.content is not None:
            return message.content
        if message.tool_payload is None:
            raise ValueError("Message content is None and no tool payload is available.")
        payload = message.to_dict().get("tool_payload")
        return json.dumps(payload, sort_keys=True)

    def _count_tokens(self, messages: List[Dict[str, Any]], system: Optional[str] = None) -> int:
        kwargs: Dict[str, Any] = {
            "model": self.model.value,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        response = self.client.messages.count_tokens(**kwargs)
        return response.input_tokens

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

        try:
            system, processed_messages = self.convert_to_anthropic_messages(messages)
            if not processed_messages:
                dummy = [{"role": "user", "content": " "}]
                total_tokens = self._count_tokens(dummy, system=system)
                prompt_tokens = self._count_tokens(dummy)
                return max(0, total_tokens - prompt_tokens)
            return self._count_tokens(processed_messages, system=system)
        except Exception as e:
            raise ValueError(f"Failed to count tokens for messages: {str(e)}")

    def count_output_tokens(self, message: Message) -> int:
        """
        Count the number of tokens in the output message using Anthropic's token counter.

        Args:
            message (Message): The output message.

        Returns:
            int: The number of output tokens.
        """
        if not message:
            return 0

        try:
            content = self._extract_message_text(message)
            if content == "":
                return 0
            if message.role == MessageRole.ASSISTANT:
                dummy_user = Message(role=MessageRole.USER, content=" ")
                total_tokens = self.count_input_tokens([dummy_user, message])
                prompt_tokens = self.count_input_tokens([dummy_user])
                return max(0, total_tokens - prompt_tokens)
            return self.count_input_tokens([message])
        except Exception as e:
            raise ValueError(f"Failed to count output tokens: {str(e)}")
