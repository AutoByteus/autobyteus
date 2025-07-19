# file: autobyteus/autobyteus/agent/bootstrap_steps/mcp_server_prewarming_step.py
import logging
from typing import TYPE_CHECKING, Set

from .base_bootstrap_step import BaseBootstrapStep
from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.server_instance_manager import McpServerInstanceManager
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.phases import AgentPhaseManager

logger = logging.getLogger(__name__)

class McpServerPrewarmingStep(BaseBootstrapStep):
    """
    Bootstrap step to eagerly start all MCP servers associated with an agent's tools.
    This ensures servers are running and ready before the agent becomes idle.
    """

    def __init__(self):
        self._config_service = McpConfigService()
        self._instance_manager = McpServerInstanceManager()
        logger.debug("McpServerPrewarmingStep initialized.")

    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Executing McpServerPrewarmingStep.")

        # 1. Find all unique server IDs by inspecting tool definitions.
        mcp_server_ids: Set[str] = set()
        for tool in context.config.tools:
            # This is the new, superior check. It relies on abstract metadata, not concrete types.
            if tool.definition and tool.definition.category == ToolCategory.MCP:
                # This is the new, superior way to get the server_id.
                # It does not rely on private attributes of the tool instance.
                server_id = tool.definition.metadata.get("mcp_server_id")
                if server_id:
                    mcp_server_ids.add(server_id)

        if not mcp_server_ids:
            logger.debug(f"Agent '{agent_id}': No MCP tools found. Skipping MCP server pre-warming.")
            return True

        logger.info(f"Agent '{agent_id}': Found {len(mcp_server_ids)} unique MCP server IDs to pre-warm: {mcp_server_ids}")

        # 2. For each server ID, unconditionally start its server instance for this agent.
        for server_id in mcp_server_ids:
            try:
                config = self._config_service.get_config(server_id)
                if not config:
                    logger.warning(f"Agent '{agent_id}': Could not find config for server_id '{server_id}' used by a tool. Cannot pre-warm.")
                    continue

                logger.info(f"Agent '{agent_id}': Pre-warming MCP server '{server_id}'.")
                # Get the instance for this agent, which creates it if it doesn't exist.
                server_instance = self._instance_manager.get_server_instance(agent_id, server_id)
                # Explicitly connect to start the server process.
                await server_instance.connect()
                logger.info(f"Agent '{agent_id}': Successfully connected to pre-warmed MCP server '{server_id}'.")

            except Exception as e:
                error_message = f"Agent '{agent_id}': Failed to pre-warm MCP server '{server_id}': {e}"
                logger.error(error_message, exc_info=True)
                # A failure to pre-warm a server is a critical bootstrap failure.
                return False
        
        return True
