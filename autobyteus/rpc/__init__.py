# file: autobyteus/autobyteus/rpc/__init__.py
"""
AutoByteUs Remote Procedure Call (RPC) Framework.

This package provides components for enabling communication between AutoByteUs agents
running in separate processes or on different machines. It includes:
- Protocol definitions for structured messaging.
- Configuration management for RPC servers.
- Client-side components for connecting to and interacting with remote agents.
- Server-side components for exposing an agent's capabilities remotely.
- High-level hosting utilities for easily serving agents.
"""

from .protocol import ProtocolMessage, MessageType, RequestType, ResponseType, ErrorCode, ErrorDetails, EventType
from .transport_type import TransportType
from .config import AgentServerConfig, AgentServerRegistry, default_agent_server_registry
from .client import (
    AbstractClientConnection,
    StdioClientConnection,
    SseClientConnection, 
    ClientConnectionManager,
    default_client_connection_manager
)
from .server import (
    AgentServerEndpoint,
    StdioServerHandler, 
    SseServerHandler, 
    BaseMethodHandler, 
    DiscoverCapabilitiesHandler, 
    InvokeMethodHandler,
    InitiateStreamDownloadHandler # Added InitiateStreamDownloadHandler
)
from .hosting import serve_agent_stdio, serve_agent_http_sse, serve_single_agent_http_sse, serve_multiple_agents_http_sse # Added all hosting functions

# RemoteAgentProxy is part of the agent package, but closely related
# from ..agent.remote_agent import RemoteAgentProxy 

__all__ = [
    # Protocol
    "ProtocolMessage",
    "MessageType",
    "RequestType",
    "ResponseType",
    "ErrorCode",
    "ErrorDetails",
    "EventType", 
    # Transport
    "TransportType",
    # Config
    "AgentServerConfig",
    "AgentServerRegistry",
    "default_agent_server_registry",
    # Client
    "AbstractClientConnection",
    "StdioClientConnection",
    "SseClientConnection", 
    "ClientConnectionManager",
    "default_client_connection_manager",
    # Server
    "AgentServerEndpoint",
    "StdioServerHandler", 
    "SseServerHandler",   
    "BaseMethodHandler",  
    "DiscoverCapabilitiesHandler", 
    "InvokeMethodHandler",
    "InitiateStreamDownloadHandler", # Added
    # Hosting
    "serve_agent_stdio", 
    "serve_agent_http_sse", # Main alias
    "serve_single_agent_http_sse", # Specific for one agent
    "serve_multiple_agents_http_sse", # Specific for multiple agents
]

