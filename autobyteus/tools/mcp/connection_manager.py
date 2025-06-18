# file: autobyteus/autobyteus/tools/mcp/connection_manager.py
from __future__ import annotations

import logging
import asyncio
from contextlib import AsyncExitStack
from dataclasses import asdict
from typing import Dict, Optional, Any, Tuple, Type

from autobyteus.utils.singleton import SingletonMeta
from .config_service import McpConfigService
from .mcp_session import McpSession
from .transport_strategies.base_client_strategy import BaseMcpClientStrategy
from .transport_strategies.sse_client_strategy import SseClientStrategy
from .transport_strategies.stdio_client_strategy import StdioClientStrategy
from .transport_strategies.streamable_http_client_strategy import StreamableHttpClientStrategy
from .transport_strategies.websocket_client_strategy import WebSocketClientStrategy
from .types import McpTransportType

logger = logging.getLogger(__name__)

class McpConnectionManager(metaclass=SingletonMeta):
    def __init__(self, config_service: McpConfigService):
        if not isinstance(config_service, McpConfigService):
            raise TypeError("McpConnectionManager requires an McpConfigService instance.")
        self._config_service: McpConfigService = config_service
        self._managed_sessions: Dict[str, McpSession] = {}
        self._lock = asyncio.Lock()
        
        self._transport_strategies: Dict[McpTransportType, Type[BaseMcpClientStrategy]] = {
            McpTransportType.STDIO: StdioClientStrategy,
            McpTransportType.STREAMABLE_HTTP: StreamableHttpClientStrategy,
            McpTransportType.SSE: SseClientStrategy,
            McpTransportType.WEBSOCKET: WebSocketClientStrategy,
        }
        logger.info(f"McpConnectionManager initialized with {len(self._transport_strategies)} transport strategies.")

    async def get_session(self, server_id: str) -> McpSession:
        async with self._lock:
            if server_id in self._managed_sessions:
                return self._managed_sessions[server_id]

            mcp_config = self._config_service.get_config(server_id)
            if not mcp_config:
                raise ValueError(f"No MCP configuration found for server_id: {server_id}")

            if not mcp_config.enabled:
                raise ValueError(f"MCP server '{server_id}' is disabled in the configuration.")
            
            try:
                strategy_class = self._transport_strategies.get(mcp_config.transport_type)
                if not strategy_class:
                    raise ValueError(f"No transport strategy found for transport type '{mcp_config.transport_type.value}' of server '{server_id}'.")
                
                # Instantiate the strategy with the specific server config
                strategy_instance = strategy_class(config=asdict(mcp_config))

                session = McpSession(
                    server_id=server_id,
                    transport_strategy=strategy_instance
                )
                await session.initialize()
                
                self._managed_sessions[server_id] = session
                logger.info(f"MCP session successfully created and stored for server_id: '{server_id}'.")
                return session

            except Exception as e:
                logger.error(f"Failed to create MCP session for server_id '{server_id}': {e}", exc_info=True)
                raise

    async def cleanup(self):
        logger.info("Closing all active MCP sessions and their resources.")
        async with self._lock:
            for server_id, session in self._managed_sessions.items():
                try:
                    await session.close()
                    logger.info(f"Successfully closed session for server_id: '{server_id}'.")
                except Exception as e:
                    logger.error(f"Error closing session for server_id '{server_id}': {e}", exc_info=True)
            self._managed_sessions.clear()
        logger.info("All MCP sessions have been requested to close.")
