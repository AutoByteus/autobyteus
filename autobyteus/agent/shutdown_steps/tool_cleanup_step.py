import asyncio
import logging
from typing import TYPE_CHECKING

from .base_shutdown_step import BaseShutdownStep

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolCleanupStep(BaseShutdownStep):
    """
    Shutdown step responsible for cleaning up all tool instances retained in the agent context.
    """

    def __init__(self):
        logger.debug("ToolCleanupStep initialized.")

    async def execute(self, context: 'AgentContext') -> bool:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Executing ToolCleanupStep.")

        tool_instances = context.tool_instances
        if not tool_instances:
            logger.debug(f"Agent '{agent_id}': No tool instances found. Skipping ToolCleanupStep.")
            return True

        all_cleanups_succeeded = True

        for tool_name, tool_instance in tool_instances.items():
            try:
                cleanup_func = getattr(tool_instance, "cleanup", None)
                if cleanup_func is None:
                    logger.debug(f"Agent '{agent_id}': Tool '{tool_name}' has no cleanup hook. Skipping.")
                    continue

                logger.info(f"Agent '{agent_id}': Cleaning up tool '{tool_name}'.")
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    cleanup_func()
                logger.debug(f"Agent '{agent_id}': Tool '{tool_name}' cleanup completed.")
            except Exception as exc:  # pragma: no cover - defensive logging
                all_cleanups_succeeded = False
                logger.error(
                    f"Agent '{agent_id}': Error during cleanup of tool '{tool_name}': {exc}",
                    exc_info=True,
                )

        if all_cleanups_succeeded:
            logger.info(f"Agent '{agent_id}': ToolCleanupStep completed successfully.")
        else:
            logger.warning(f"Agent '{agent_id}': ToolCleanupStep completed with errors; see logs above.")

        return all_cleanups_succeeded
