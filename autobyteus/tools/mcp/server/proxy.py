# file: autobyteus/autobyteus/tools/mcp/server/proxy.py
import logging
from typing import Any, Dict

from ..server_instance_manager import McpServerInstanceManager

logger = logging.getLogger(__name__)

class McpServerProxy:
    """
    A proxy object that provides the interface of a BaseManagedMcpServer
    but delegates the actual work to a real server instance retrieved from the
    McpServerInstanceManager. This decouples the tool from the manager.
    """
    def __init__(self, agent_id: str, server_id: str):
        if not agent_id or not server_id:
            raise ValueError("McpServerProxy requires both agent_id and server_id.")
        self._agent_id = agent_id
        self._server_id = server_id
        self._instance_manager = McpServerInstanceManager()
        logger.debug(f"McpServerProxy created for agent '{agent_id}' and server '{server_id}'.")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Gets the real server instance from the manager and delegates the tool call.
        """
        logger.debug(f"Proxy: Getting server instance for agent '{self._agent_id}', server '{self._server_id}'.")
        # The manager handles the logic of creating or returning a cached instance.
        real_server_instance = self._instance_manager.get_server_instance(
            agent_id=self._agent_id,
            server_id=self._server_id
        )
        
        logger.debug(f"Proxy: Delegating 'call_tool({tool_name})' to real server instance.")
        # The real instance handles its own connection state.
        return await real_server_instance.call_tool(tool_name, arguments)
