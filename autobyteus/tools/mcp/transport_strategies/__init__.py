# file: autobyteus/autobyteus/tools/mcp/transport_strategies/__init__.py
"""
This package contains the transport client strategies for the MCP Connection Manager.
Each strategy handles the specifics of establishing a connection for a particular
MCP transport type (e.g., STDIO, Streamable HTTP, SSE).
"""

from .base_client_strategy import McpTransportClientStrategy
from .stdio_client_strategy import StdioClientStrategy
from .streamable_http_client_strategy import StreamableHttpClientStrategy
from .sse_client_strategy import SseClientStrategy

__all__ = [
    "McpTransportClientStrategy",
    "StdioClientStrategy",
    "StreamableHttpClientStrategy",
    "SseClientStrategy",
]
