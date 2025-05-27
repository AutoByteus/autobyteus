# file: autobyteus/autobyteus/mcp/__init__.py
"""
This package implements the Model Context Protocol (MCP) integration for AutoByteUs.
It allows AutoByteUs to connect to external MCP servers, discover tools,
and register them as standard AutoByteUs tools.
"""
import logging

logger = logging.getLogger(__name__)

# The actual 'mcp' library and its components (e.g., mcp.ClientSession, mcp.metadata.ToolMetadata,
# mcp.stdio_client, mcp.transports.SSETransport) are expected to be installed in the environment
# and imported directly by the modules within this package (like connection_manager.py, registrar.py).
# This __init__.py file primarily serves to make this 'mcp' directory a package and
# to export its key public components for use by other parts of AutoByteUs.

logger.info("AutoByteUs MCP integration package initialized. Expects 'mcp' library to be available.")

# Import from types.py for data classes
# CORRECTED: Removed McpConfig, StdioServerParametersConfig, SseTransportConfig, StreamableHttpConfig
from .types import (
    BaseMcpConfig,
    StdioMcpServerConfig,
    SseMcpServerConfig,
    StreamableHttpMcpServerConfig,
    McpTransportType
)
# Import McpConfigService from config_service.py
from .config_service import McpConfigService

from .connection_manager import McpConnectionManager
from .schema_mapper import McpSchemaMapper 
from .tool import GenericMcpTool
from .registrar import McpToolRegistrar

__all__ = [
    # Types from types.py
    "BaseMcpConfig",
    "StdioMcpServerConfig",
    "SseMcpServerConfig",
    "StreamableHttpMcpServerConfig",
    "McpTransportType",
    # Service from config_service.py
    "McpConfigService",
    # Other components
    "McpConnectionManager",
    "McpSchemaMapper",
    "GenericMcpTool",
    "McpToolRegistrar",
]
