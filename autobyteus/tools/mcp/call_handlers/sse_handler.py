# file: autobyteus/autobyteus/tools/mcp/call_handlers/sse_handler.py
import logging
from typing import Dict, Any, TYPE_CHECKING

from .base_handler import McpCallHandler

if TYPE_CHECKING:
    from ..types import BaseMcpConfig

logger = logging.getLogger(__name__)

class SseMcpCallHandler(McpCallHandler):
    """Placeholder handler for MCP tool calls over SSE."""

    async def handle_call(
        self, 
        config: 'BaseMcpConfig', 
        remote_tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        logger.warning(f"SseMcpCallHandler for server '{config.server_id}' is a placeholder and not fully implemented.")
        raise NotImplementedError(f"SSE transport is not fully implemented for tool call to '{remote_tool_name}'.")
