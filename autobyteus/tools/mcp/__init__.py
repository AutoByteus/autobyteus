# file: autobyteus/autobyteus/mcp/__init__.py
"""
This package implements the Model Context Protocol (MCP) integration for AutoByteUs.
It allows AutoByteUs to connect to external MCP servers, discover tools,
and register them as standard AutoByteUs tools using a stateful, server-centric
architecture with per-agent isolation.
"""
import logging

logger = logging.getLogger(__name__)

# The actual 'mcp' library and its components are expected to be installed 
# in the environment and are used by the internal components.

logger.info("AutoByteUs MCP integration package initialized. Expects 'mcp' library to be available.")

# Import from types.py for data classes
from .types import (
    BaseMcpConfig,
    StdioMcpServerConfig,
    StreamableHttpMcpServerConfig,
    McpTransportType,
    McpServerInstanceKey,
)
# Import McpConfigService from config_service.py
from .config_service import McpConfigService

# Key components of the integration
from .schema_mapper import McpSchemaMapper 
from .tool import GenericMcpTool
from .factory import McpToolFactory
from .tool_registrar import McpToolRegistrar
from .server_instance_manager import McpServerInstanceManager

__all__ = [
    # Types from types.py
    "BaseMcpConfig",
    "StdioMcpServerConfig",
    "StreamableHttpMcpServerConfig",
    "McpTransportType",
    "McpServerInstanceKey",
    # Services and Managers
    "McpConfigService",
    "McpServerInstanceManager",
    # Other public components
    "McpSchemaMapper",
    "GenericMcpTool",
    "McpToolFactory",
    "McpToolRegistrar",
]
