# file: autobyteus/autobyteus/tools/mcp/server_instance_manager.py
import logging
from typing import Dict, List, AsyncIterator
from contextlib import asynccontextmanager

from autobyteus.utils.singleton import SingletonMeta
from .config_service import McpConfigService
from .server import BaseManagedMcpServer, StdioManagedMcpServer, HttpManagedMcpServer
from .types import McpTransportType, McpServerInstanceKey, BaseMcpConfig

logger = logging.getLogger(__name__)

class McpServerInstanceManager(metaclass=SingletonMeta):
    """
    Manages the lifecycle of BaseManagedMcpServer instances, providing
    isolated server connections on a per-agent, per-server_id basis.
    """
    def __init__(self):
        self._config_service = McpConfigService()
        self._active_servers: Dict[McpServerInstanceKey, BaseManagedMcpServer] = {}
        logger.info("McpServerInstanceManager initialized.")
    
    def _create_server_instance(self, server_config: BaseMcpConfig) -> BaseManagedMcpServer:
        """Factory method to create a server instance from a config."""
        if server_config.transport_type == McpTransportType.STDIO:
            return StdioManagedMcpServer(server_config)
        elif server_config.transport_type == McpTransportType.STREAMABLE_HTTP:
            return HttpManagedMcpServer(server_config)
        else:
            raise NotImplementedError(f"No ManagedMcpServer implementation for transport type '{server_config.transport_type}'.")

    def get_server_instance(self, agent_id: str, server_id: str) -> BaseManagedMcpServer:
        """
        Retrieves or creates a dedicated, long-lived managed server instance
        for a given agent and server ID.
        """
        instance_key = McpServerInstanceKey(agent_id=agent_id, server_id=server_id)
        
        if instance_key in self._active_servers:
            return self._active_servers[instance_key]

        logger.info(f"Creating new persistent server instance for {instance_key}.")
        config = self._config_service.get_config(server_id)
        if not config:
            raise ValueError(f"No configuration found for server_id '{server_id}'.")

        server_instance = self._create_server_instance(config)
        self._active_servers[instance_key] = server_instance
        return server_instance

    @asynccontextmanager
    async def managed_discovery_session(self, server_config: BaseMcpConfig) -> AsyncIterator[BaseManagedMcpServer]:
        """
        Provides a temporary server instance for a one-shot operation like discovery.
        Guarantees the instance is closed upon exiting the context.
        This method uses the provided config object directly and does not look it up
        in the config service, making it suitable for stateless previews.
        """
        if not server_config:
            raise ValueError("A valid BaseMcpConfig object must be provided to managed_discovery_session.")
        
        logger.debug(f"Creating temporary discovery instance for server '{server_config.server_id}'.")
        temp_server_instance = self._create_server_instance(server_config)
        try:
            yield temp_server_instance
        finally:
            logger.debug(f"Closing temporary discovery instance for server '{server_config.server_id}'.")
            await temp_server_instance.close()

    async def cleanup_mcp_server_instances_for_agent(self, agent_id: str):
        """
        Closes all active MCP server instances and removes them from the cache for a specific agent.
        """
        logger.info(f"Cleaning up all MCP server instances for agent '{agent_id}'.")
        keys_to_remove: List[McpServerInstanceKey] = []
        for instance_key, server_instance in self._active_servers.items():
            if instance_key.agent_id == agent_id:
                try:
                    await server_instance.close()
                except Exception as e:
                    logger.error(f"Error closing MCP server '{instance_key.server_id}' for agent '{instance_key.agent_id}': {e}", exc_info=True)
                keys_to_remove.append(instance_key)
        
        for key in keys_to_remove:
            del self._active_servers[key]
        logger.info(f"Finished cleaning up MCP server instances for agent '{agent_id}'.")

    async def cleanup_all_mcp_server_instances(self):
        """Closes all active MCP server instances for all agents and clears the cache."""
        logger.info("Cleaning up all active MCP server instances.")
        agent_ids = {key.agent_id for key in self._active_servers.keys()}
        for agent_id in agent_ids:
            await self.cleanup_mcp_server_instances_for_agent(agent_id)
