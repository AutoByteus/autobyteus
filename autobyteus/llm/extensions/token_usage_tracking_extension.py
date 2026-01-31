from typing import Optional, List, TYPE_CHECKING, Any
import logging
from autobyteus.llm.extensions.base_extension import LLMExtension
from autobyteus.llm.token_counter.token_counter_factory import get_token_counter
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.token_usage_tracker import TokenUsageTracker
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.response_types import CompleteResponse

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

logger = logging.getLogger(__name__)

class TokenUsageTrackingExtension(LLMExtension):
    """
    Extension that tracks and monitors token usage and associated costs for LLM interactions.
    When no token counter is available for the provider, the extension operates in disabled mode
    and returns zero/None for all metrics.
    """

    def __init__(self, llm: "BaseLLM"):
        super().__init__(llm)
        self.token_counter = get_token_counter(llm.model, llm)
        if self.token_counter is not None:
            self.usage_tracker = TokenUsageTracker(llm.model, self.token_counter)
        else:
            self.usage_tracker = None
        self._latest_usage: Optional[TokenUsage] = None

    @property
    def is_enabled(self) -> bool:
        """Check if token tracking is enabled (token counter is available)."""
        return self.token_counter is not None

    @property
    def latest_token_usage(self) -> Optional[TokenUsage]:
        """Get the latest token usage information."""
        return self._latest_usage

    async def before_invoke(
        self, messages: List[Message], rendered_payload: Optional[Any] = None, **kwargs
    ) -> None:
        if not self.is_enabled:
            return
        if not messages:
            logger.warning("TokenUsageTrackingExtension.before_invoke received empty messages list.")
            return
        self.usage_tracker.calculate_input_messages(messages)

    async def after_invoke(
        self, messages: List[Message], response: CompleteResponse = None, **kwargs
    ) -> None:
        """
        Get the latest usage from tracker and optionally override token counts with provider's usage if available
        """
        if not self.is_enabled:
            return

        latest_usage = self.usage_tracker.get_latest_usage()
    
        if latest_usage is None:
            logger.warning(
                "No token usage record found in after_invoke. This may indicate the LLM implementation "
                "did not call before_invoke. Skipping token usage update for this call."
            )
            return

        if isinstance(response, CompleteResponse) and response.usage:
            # Override token counts with provider's data if available
            latest_usage.prompt_tokens = response.usage.prompt_tokens
            latest_usage.completion_tokens = response.usage.completion_tokens
            latest_usage.total_tokens = response.usage.total_tokens
        elif isinstance(response, CompleteResponse) and response.content:
            # Fallback: estimate completion tokens from response content
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                reasoning_content=response.reasoning,
            )
            latest_usage.completion_tokens = self.token_counter.count_output_tokens(assistant_message)
            latest_usage.total_tokens = latest_usage.prompt_tokens + latest_usage.completion_tokens

        # Always calculate costs using current token counts
        latest_usage.prompt_cost = self.usage_tracker.calculate_cost(
            latest_usage.prompt_tokens, True)
        latest_usage.completion_cost = self.usage_tracker.calculate_cost(
            latest_usage.completion_tokens, False)
        latest_usage.total_cost = latest_usage.prompt_cost + latest_usage.completion_cost

        self._latest_usage = latest_usage

    def get_total_cost(self) -> float:
        if not self.is_enabled:
            return 0.0
        return self.usage_tracker.get_total_cost()

    def get_usage_history(self) -> List[TokenUsage]:
        if not self.is_enabled:
            return []
        return self.usage_tracker.get_usage_history()

    def get_total_input_tokens(self) -> int:
        if not self.is_enabled:
            return 0
        return self.usage_tracker.get_total_input_tokens()

    def get_total_output_tokens(self) -> int:
        if not self.is_enabled:
            return 0
        return self.usage_tracker.get_total_output_tokens()

    async def cleanup(self):
        if self.usage_tracker is not None:
            self.usage_tracker.clear_history()
        self._latest_usage = None
