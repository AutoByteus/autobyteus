# file: autobyteus/autobyteus/tools/mcp/call_handlers/websocket_handler.py
import logging
from typing import Any, Dict, Optional

from mcp import types as mcp_types
from ..transport_strategies.websocket_client_strategy import WebSocketClientStrategy
from .base_handler import McpCallHandler
from ..types import BaseMcpConfig

logger = logging.getLogger(__name__)

class WebSocketMcpCallHandler(McpCallHandler):
    """
    Handler for MCP calls over WebSocket transport.
    """
    def __init__(self):
        super().__init__()
        logger.info("WebSocketMcpCallHandler initialized")
    
    async def handle_call(
        self, 
        config: BaseMcpConfig,
        remote_tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Handles the invocation of an MCP tool call over WebSockets.
        
        Args:
            config: The MCP server configuration to use
            remote_tool_name: The name of the remote tool to call
            arguments: The arguments to pass to the remote tool

        Returns:
            The result of the MCP call, if any
        """
        logger.debug(f"WebSocketMcpCallHandler handling call to '{remote_tool_name}' with arguments: {arguments}")
        
        # Create a WebSocket client strategy with config
        strategy_config = {"uri": config.uri}
        strategy = WebSocketClientStrategy(config=strategy_config)
        
        try:
            # Connect to the WebSocket server
            await strategy.connect()
            
            # Prepare the MCP request
            request = {
                "method": remote_tool_name,
                "params": arguments,
                "id": "1"  # Simple ID for now
            }
            
            # Send the request
            await strategy.send(request)
            
            # For simplicity, we're assuming a response will come through the listener
            # In a real implementation, we would wait for the specific response with this ID
            # This is a placeholder - actual implementation would need response handling
            result = {"success": True}
            
            logger.debug(f"WebSocketMcpCallHandler call to '{remote_tool_name}' completed with result type: {type(result)}")
            return result
            
        except Exception as e:
            logger.error(f"WebSocketMcpCallHandler failed to handle call to '{remote_tool_name}': {e}", exc_info=True)
            raise
        finally:
            # Clean up the client connection
            try:
                await strategy.disconnect()
            except Exception as cleanup_err:
                logger.warning(f"Error during WebSocketClientStrategy cleanup: {cleanup_err}") 