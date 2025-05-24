# file: autobyteus/autobyteus/rpc/server/__init__.py
"""
Server-side components for the AutoByteUs RPC framework.
These components enable an AgentRuntime to expose its capabilities remotely.
"""
from .base_method_handler import BaseMethodHandler
from .method_handlers import DiscoverCapabilitiesHandler, InvokeMethodHandler, InitiateStreamDownloadHandler # Added InitiateStreamDownloadHandler
from .stdio_server_handler import StdioServerHandler
from .sse_server_handler import SseServerHandler 
from .agent_server_endpoint import AgentServerEndpoint

__all__ = [
    "BaseMethodHandler",
    "DiscoverCapabilitiesHandler",
    "InvokeMethodHandler",
    "InitiateStreamDownloadHandler", # Added InitiateStreamDownloadHandler
    "StdioServerHandler",
    "SseServerHandler", 
    "AgentServerEndpoint",
]
