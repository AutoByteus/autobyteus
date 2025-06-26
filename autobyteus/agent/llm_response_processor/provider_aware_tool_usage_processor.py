# file: autobyteus/autobyteus/agent/llm_response_processor/provider_aware_tool_usage_processor.py
import logging
from typing import TYPE_CHECKING

from .base_processor import BaseLLMResponseProcessor
from autobyteus.tools.usage.parsers import ProviderAwareToolUsageParser
from autobyteus.tools.usage.parsers.exceptions import ToolUsageParseException
from autobyteus.agent.events import PendingToolInvocationEvent

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import LLMCompleteResponseReceivedEvent
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class ProviderAwareToolUsageProcessor(BaseLLMResponseProcessor):
    """
    A "master" tool usage processor that uses a high-level parser from the
    `tools` module to extract tool invocations, and then enqueues the
    necessary agent events based on the parsed results.
    """
    def __init__(self):
        self._parser = ProviderAwareToolUsageParser()
        logger.debug("ProviderAwareToolUsageProcessor initialized.")

    @classmethod
    def get_name(cls) -> str:
        return "provider_aware_tool_usage"

    async def process_response(self, response: 'CompleteResponse', context: 'AgentContext', triggering_event: 'LLMCompleteResponseReceivedEvent') -> bool:
        """
        Uses a ProviderAwareToolUsageParser to get a list of tool invocations,
        and then enqueues a PendingToolInvocationEvent for each one.
        Propagates ToolUsageParseException if parsing fails.
        """
        try:
            # Delegate parsing to the high-level parser
            tool_invocations = self._parser.parse(response, context)
        except ToolUsageParseException:
            # Re-raise the exception to be caught by the event handler
            raise

        if not tool_invocations:
            return False

        logger.info(f"Agent '{context.agent_id}': Parsed {len(tool_invocations)} tool invocations. Enqueuing events.")
        for invocation in tool_invocations:
            logger.info(f"Agent '{context.agent_id}' ({self.get_name()}) identified tool invocation: {invocation.name}. Enqueuing event.")
            await context.input_event_queues.enqueue_tool_invocation_request(
                PendingToolInvocationEvent(tool_invocation=invocation)
            )
        
        return True
