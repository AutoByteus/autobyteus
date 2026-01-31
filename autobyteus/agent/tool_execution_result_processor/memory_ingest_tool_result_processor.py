import logging
from typing import TYPE_CHECKING

from autobyteus.agent.tool_execution_result_processor.base_processor import BaseToolExecutionResultProcessor

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import ToolResultEvent

logger = logging.getLogger(__name__)


class MemoryIngestToolResultProcessor(BaseToolExecutionResultProcessor):
    @classmethod
    def get_order(cls) -> int:
        return 900

    async def process(self, event: "ToolResultEvent", context: "AgentContext") -> "ToolResultEvent":
        memory_manager = getattr(context.state, "memory_manager", None)
        if memory_manager:
            if event.turn_id:
                memory_manager.ingest_tool_result(event)
                logger.debug("MemoryIngestToolResultProcessor stored tool result for turn_id %s", event.turn_id)
            else:
                logger.debug(
                    "MemoryIngestToolResultProcessor skipping tool result without turn_id for tool '%s'",
                    event.tool_name,
                )
        return event
