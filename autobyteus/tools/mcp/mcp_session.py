import asyncio
import logging
from typing import Optional, List, Dict, Any
from collections import namedtuple

from autobyteus.tools.mcp.transport_strategies.base_client_strategy import BaseMcpClientStrategy

logger = logging.getLogger(__name__)

# A simple structure to mimic the expected mcp_types.Tool
ToolInfo = namedtuple("ToolInfo", ["name", "description", "inputSchema"])

# A simple structure to mimic mcp_types.ListToolsResult
ListToolsResult = namedtuple("ListToolsResult", ["tools"])

class McpSession:
    """Represents and manages a session with a single MCP server."""

    def __init__(self, server_id: str, transport_strategy: BaseMcpClientStrategy):
        if not server_id or not isinstance(server_id, str):
            raise ValueError("server_id must be a non-empty string.")
        if not transport_strategy or not isinstance(transport_strategy, BaseMcpClientStrategy):
            raise TypeError("transport_strategy must be an instance of BaseMcpClientStrategy.")
            
        self.server_id = server_id
        self.transport_strategy = transport_strategy
        self._is_initialized = False

    async def initialize(self):
        """Initializes the session by connecting the transport strategy."""
        if self._is_initialized:
            logger.debug(f"Session for '{self.server_id}' is already initialized.")
            return
            
        logger.debug(f"Initializing session for MCP server: '{self.server_id}'...")
        try:
            await self.transport_strategy.connect()
            # Add a small delay to allow the connection state to propagate
            await asyncio.sleep(0.05)
            self._is_initialized = True
            logger.info(f"MCP Session for '{self.server_id}' initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MCP session for '{self.server_id}': {e}", exc_info=True)
            # Ensure we don't leave it in a partially initialized state
            self._is_initialized = False
            raise

    async def close(self):
        """Closes the session and its underlying transport."""
        if not self._is_initialized:
            logger.debug(f"Session for '{self.server_id}' was not initialized, skipping close.")
            return

        logger.debug(f"Closing session for MCP server: '{self.server_id}'...")
        try:
            await self.transport_strategy.disconnect()
            logger.info(f"MCP Session for '{self.server_id}' closed successfully.")
        except Exception as e:
            logger.error(f"Error while closing MCP session for '{self.server_id}': {e}", exc_info=True)
        finally:
            self._is_initialized = False

    @property
    def is_connected(self) -> bool:
        """Checks if the underlying transport is connected."""
        return self.transport_strategy.is_connected

    async def list_tools(self) -> ListToolsResult:
        """Performs an RPC call to list tools and formats the response."""
        logger.debug(f"Requesting to list tools from server '{self.server_id}'...")
        result_list = await self.transport_strategy.rpc_call("tools/list")
        
        if not isinstance(result_list, list):
            logger.error(f"Received invalid format for tool list from '{self.server_id}': {result_list}")
            return ListToolsResult(tools=[])

        tools = []
        for tool_data in result_list:
            tools.append(ToolInfo(
                name=tool_data.get("name"),
                description=tool_data.get("description"),
                inputSchema=tool_data.get("inputSchema")
            ))
        
        logger.debug(f"Successfully parsed {len(tools)} tools from server '{self.server_id}'.")
        return ListToolsResult(tools=tools)

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Calls a tool on the remote MCP server.
        
        Args:
            tool_name: The name of the tool to call.
            parameters: The parameters to pass to the tool.
            
        Returns:
            The result of the tool execution.
            
        Raises:
            ConnectionError: If the session is not connected.
            RuntimeError: If the tool call fails.
        """
        logger.debug(f"Calling tool '{tool_name}' on server '{self.server_id}' with parameters: {parameters}")
        
        if not self.is_connected:
            logger.error(f"Cannot call tool: session for '{self.server_id}' is not connected.")
            raise ConnectionError(f"MCP Session for '{self.server_id}' is not connected.")
        
        try:
            result = await self.transport_strategy.rpc_call(
                "tools/call", 
                params={
                    "tool_name": tool_name,
                    "parameters": parameters
                }
            )
            logger.debug(f"Tool '{tool_name}' call successful. Result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}' on server '{self.server_id}': {e}", exc_info=True)
            raise RuntimeError(f"Failed to call tool '{tool_name}': {e}")

    async def send_message(self, message: dict):
        """Sends a message through the transport strategy."""
        if not self.is_connected:
            logger.error(f"Cannot send message: session for '{self.server_id}' is not connected.")
            # Or consider attempting a reconnect here
            raise ConnectionError(f"MCP Session for '{self.server_id}' is not connected.")
        await self.transport_strategy.send(message)

    async def listen_for_messages(self):
        """Registers a callback for incoming messages."""
        # This is now handled by the background task in the WebSocket strategy,
        # but we could expose a way to add more handlers here if needed.
        pass 