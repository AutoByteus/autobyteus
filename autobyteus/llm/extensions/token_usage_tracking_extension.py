
from typing import Optional, List, TYPE_CHECKING
from autobyteus.llm.extensions.base_extension import LLMExtension
from autobyteus.llm.token_counter.token_counter_factory import get_token_counter
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.token_usage_tracker import TokenUsageTracker
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.response_types import CompleteResponse

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

class TokenUsageTrackingExtension(LLMExtension):
    """
    Extension that tracks and monitors token usage and associated costs for LLM interactions.
    """

    def __init__(self, llm: "BaseLLM"):
        super().__init__(llm)
        self.token_counter = get_token_counter(llm.model, llm)
        self.usage_tracker = TokenUsageTracker(llm.model, self.token_counter)
        self._latest_usage: Optional[TokenUsage] = None

    @property
    def latest_token_usage(self) -> Optional[TokenUsage]:
        """Get the latest token usage information."""
        return self._latest_usage

    async def before_invoke(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> None:
        pass

    async def after_invoke(
        self, user_message: str, file_paths: Optional[List[str]] = None, response: CompleteResponse = None, **kwargs
    ) -> None:
        """
        Get the latest usage from tracker and optionally override token counts with provider's usage if available
        """
        latest_usage = self.usage_tracker.get_latest_usage()
        
        if isinstance(response, CompleteResponse) and response.usage:
            # Override token counts with provider's data if available
            latest_usage.prompt_tokens = response.usage.prompt_tokens
            latest_usage.completion_tokens = response.usage.completion_tokens
            latest_usage.total_tokens = response.usage.total_tokens
            
        # Always calculate costs using current token counts
        latest_usage.prompt_cost = self.usage_tracker.calculate_cost(
            latest_usage.prompt_tokens, True)
        latest_usage.completion_cost = self.usage_tracker.calculate_cost(
            latest_usage.completion_tokens, False)
        latest_usage.total_cost = latest_usage.prompt_cost + latest_usage.completion_cost
                
        self._latest_usage = latest_usage

    def on_user_message_added(self, message: Message) -> None:
        """Track usage whenever a user message is added. Here input message argument is not used, because the input token counts should consider all the input messages"""
        self.usage_tracker.calculate_input_messages(self.llm.messages)

    def on_assistant_message_added(self, message: Message) -> None:
        """Track usage whenever an assistant message is added."""
        self.usage_tracker.calculate_output_message(message)

    def get_total_cost(self) -> float:
        return self.usage_tracker.get_total_cost()

    def get_usage_history(self) -> List[TokenUsage]:
        return self.usage_tracker.get_usage_history()

    def get_total_input_tokens(self) -> int:
        return self.usage_tracker.get_total_input_tokens()

    def get_total_output_tokens(self) -> int:
        return self.usage_tracker.get_total_output_tokens()

    async def cleanup(self):
        self.usage_tracker.clear_history()
        self._latest_usage = None
