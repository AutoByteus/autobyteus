# file: autobyteus/autobyteus/agent/shutdown_steps/mcp_server_cleanup_step.py
import logging
from typing import TYPE_CHECKING

from .base_shutdown_step import BaseShutdownStep
from autobyteus.tools.mcp.server_instance_manager import McpServerInstanceManager

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class McpServerCleanupStep(BaseShutdownStep):
    """
    Shutdown step for cleaning up all MCP server instances associated with an agent.
    """
    def __init__(self):
        self._instance_manager = McpServerInstanceManager()
        logger.debug("McpServerCleanupStep initialized.")

    async def execute(self, context: 'AgentContext') -> bool:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Executing McpServerCleanupStep.")

        try:
            await self._instance_manager.cleanup_mcp_server_instances_for_agent(agent_id)
            logger.info(f"Agent '{agent_id}': MCP server instance cleanup completed successfully.")
            return True
        except Exception as e:
            error_message = f"Agent '{agent_id}': Critical failure during McpServerCleanupStep: {e}"
            logger.error(error_message, exc_info=True)
            return False
