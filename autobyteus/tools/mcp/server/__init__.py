# file: autobyteus/autobyteus/tools/mcp/server/__init__.py
"""
This package contains the core abstractions for managing connections to remote MCP servers.
"""
from .base_managed_mcp_server import BaseManagedMcpServer, ServerState
from .stdio_managed_mcp_server import StdioManagedMcpServer
from .http_managed_mcp_server import HttpManagedMcpServer
from .proxy import McpServerProxy

__all__ = [
    "BaseManagedMcpServer",
    "ServerState",
    "StdioManagedMcpServer",
    "HttpManagedMcpServer",
    "McpServerProxy",
]
