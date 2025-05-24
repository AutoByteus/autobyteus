# file: autobyteus/autobyteus/rpc/config/agent_server_registry.py
import logging
from typing import Dict, Optional, List

from autobyteus.utils.singleton import SingletonMeta
from .agent_server_config import AgentServerConfig

logger = logging.getLogger(__name__)

class AgentServerRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for storing and managing AgentServerConfig objects.
    This allows different parts of the system to retrieve server connection
    details by a server_id.
    """

    def __init__(self):
        """Initializes the AgentServerRegistry with an empty store."""
        self._configs: Dict[str, AgentServerConfig] = {}
        logger.info("AgentServerRegistry initialized.")

    def register_config(self, config: AgentServerConfig) -> None:
        """
        Registers an agent server configuration.
        If a configuration with the same server_id already exists, it will be
        overwritten, and a warning will be logged.

        Args:
            config: The AgentServerConfig object to register.

        Raises:
            TypeError: If the provided config is not an AgentServerConfig instance.
        """
        if not isinstance(config, AgentServerConfig):
            raise TypeError(f"Expected AgentServerConfig instance, got {type(config).__name__}.")

        if config.server_id in self._configs:
            logger.warning(f"Overwriting existing agent server configuration for server_id: '{config.server_id}'.")
        
        self._configs[config.server_id] = config
        logger.info(f"AgentServerConfig for server_id '{config.server_id}' (transport: {config.transport_type.value}) registered.")

    def get_config(self, server_id: str) -> Optional[AgentServerConfig]:
        """
        Retrieves an agent server configuration by its server_id.

        Args:
            server_id: The unique identifier of the server configuration.

        Returns:
            The AgentServerConfig object if found, otherwise None.
        """
        if not isinstance(server_id, str):
            logger.warning(f"Attempted to retrieve agent server config with non-string server_id: {type(server_id).__name__}.")
            return None
        
        config = self._configs.get(server_id)
        if not config:
            logger.debug(f"AgentServerConfig with server_id '{server_id}' not found in registry.")
        return config

    def unregister_config(self, server_id: str) -> bool:
        """
        Removes an agent server configuration from the registry.

        Args:
            server_id: The server_id of the configuration to remove.

        Returns:
            True if the configuration was found and removed, False otherwise.
        """
        if not isinstance(server_id, str):
            logger.warning(f"Attempted to unregister agent server config with non-string server_id: {type(server_id).__name__}.")
            return False

        if server_id in self._configs:
            removed_config = self._configs.pop(server_id)
            logger.info(f"AgentServerConfig for server_id '{removed_config.server_id}' unregistered successfully.")
            return True
        else:
            logger.warning(f"AgentServerConfig with server_id '{server_id}' not found for unregistration.")
            return False

    def list_server_ids(self) -> List[str]:
        """Returns a list of all registered server_ids."""
        return list(self._configs.keys())

    def get_all_configs(self) -> Dict[str, AgentServerConfig]:
        """Returns a shallow copy of all registered configurations."""
        return dict(self._configs)

    def clear(self) -> None:
        """Removes all configurations from the registry."""
        count = len(self._configs)
        self._configs.clear()
        logger.info(f"Cleared {count} configurations from the AgentServerRegistry.")

    def __len__(self) -> int:
        return len(self._configs)

    def __contains__(self, server_id: str) -> bool:
        if isinstance(server_id, str):
            return server_id in self._configs
        return False

# Default global instance of the registry
default_agent_server_registry = AgentServerRegistry()

if __name__ == "__main__": # pragma: no cover
    logging.basicConfig(level=logging.DEBUG)

    registry = default_agent_server_registry # Use the default instance

    # Stdio Config
    stdio_config_data = {
        "server_id": "local_agent_stdio_main",
        "transport_type": "stdio",
        "stdio_command": ["python", "-m", "some_module"]
    }
    stdio_conf = AgentServerConfig(**stdio_config_data)
    registry.register_config(stdio_conf)

    # SSE Config
    sse_config_data = {
        "server_id": "remote_agent_sse_main",
        "transport_type": "sse",
        "sse_base_url": "http://localhost:8080"
    }
    sse_conf = AgentServerConfig(**sse_config_data)
    registry.register_config(sse_conf)

    logger.info(f"Registered server IDs: {registry.list_server_ids()}")
    
    retrieved_stdio = registry.get_config("local_agent_stdio_main")
    if retrieved_stdio:
        logger.info(f"Retrieved Stdio Config: {retrieved_stdio.stdio_command}")
    
    retrieved_sse = registry.get_config("remote_agent_sse_main")
    if retrieved_sse:
        logger.info(f"Retrieved SSE Config URL: {retrieved_sse.get_sse_full_request_url()}")

    assert "local_agent_stdio_main" in registry
    assert len(registry) == 2

    registry.unregister_config("local_agent_stdio_main")
    assert "local_agent_stdio_main" not in registry
    logger.info(f"After unregistering, server IDs: {registry.list_server_ids()}")

    registry.clear()
    assert len(registry) == 0
    logger.info(f"After clearing, server IDs: {registry.list_server_ids()}")

