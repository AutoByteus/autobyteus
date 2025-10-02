# file: autobyteus/autobyteus/agent/llm_response_processor/provider_aware_tool_usage_processor.py
import logging
from typing import TYPE_CHECKING, List

from .base_processor import BaseLLMResponseProcessor
from autobyteus.agent.events import PendingToolInvocationEvent
from autobyteus.agent.tool_invocation import ToolInvocation, ToolInvocationTurn
from autobyteus.tools.usage.parsers import ProviderAwareToolUsageParser
from autobyteus.tools.usage.parsers.exceptions import ToolUsageParseException

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import LLMCompleteResponseReceivedEvent
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class ProviderAwareToolUsageProcessor(BaseLLMResponseProcessor):
    """
    A "master" tool usage processor that uses a high-level parser from the
    `tools` module to extract tool invocations. It then ensures each invocation
    has a session-unique ID before enqueuing the necessary agent events.
    """
    INVOCATION_COUNTS_KEY = "agent_tool_invocation_counts"

    def __init__(self):
        self._parser = ProviderAwareToolUsageParser()
        logger.debug("ProviderAwareToolUsageProcessor initialized.")

    @classmethod
    def get_name(cls) -> str:
        return "ProviderAwareToolUsageProcessor"

    @classmethod
    def get_order(cls) -> int:
        """Runs with the highest priority to parse for tool calls before any other processing."""
        return 100

    @classmethod
    def is_mandatory(cls) -> bool:
        """This processor is essential for any agent that uses tools."""
        return True

    async def process_response(self, response: 'CompleteResponse', context: 'AgentContext', triggering_event: 'LLMCompleteResponseReceivedEvent') -> bool:
        """
        Uses a ProviderAwareToolUsageParser to get tool invocations, makes their
        IDs unique within the agent's session, and then enqueues a
        PendingToolInvocationEvent for each one.
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

        # --- NEW LOGIC FOR UNIQUE ID GENERATION ---
        
        # Ensure the counter map exists in the agent's state's custom data
        if self.INVOCATION_COUNTS_KEY not in context.custom_data:
            context.custom_data[self.INVOCATION_COUNTS_KEY] = {}
        
        invocation_counts = context.custom_data[self.INVOCATION_COUNTS_KEY]
        
        processed_invocations: List[ToolInvocation] = []

        for invocation in tool_invocations:
            base_id = invocation.id
            
            # Get the current count for this base ID, default to 0
            count = invocation_counts.get(base_id, 0)
            
            # Create the new session-unique ID
            unique_id = f"{base_id}_{count}"
            
            # Update the invocation's ID in-place
            invocation.id = unique_id
            
            # Increment the counter for the next time this base ID is seen
            invocation_counts[base_id] = count + 1
            
            processed_invocations.append(invocation)

        # --- END NEW LOGIC ---
        
        # --- NEW: Initialize the multi-tool turn state ---
        if len(processed_invocations) > 0:
            logger.info(f"Agent '{context.agent_id}': Initializing multi-tool call turn with {len(processed_invocations)} invocations.")
            context.state.active_multi_tool_call_turn = ToolInvocationTurn(invocations=processed_invocations)
        # --- END NEW ---

        logger.info(f"Agent '{context.agent_id}': Parsed {len(processed_invocations)} tool invocations. Enqueuing events with unique IDs.")
        for invocation in processed_invocations:
            logger.info(f"Agent '{context.agent_id}' ({self.get_name()}) identified tool invocation: {invocation.name} with unique ID {invocation.id}. Enqueuing event.")
            await context.input_event_queues.enqueue_tool_invocation_request(
                PendingToolInvocationEvent(tool_invocation=invocation)
            )
        
        return True
