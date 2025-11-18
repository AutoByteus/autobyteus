# file: autobyteus/autobyteus/tools/mcp/types.py
import logging
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass, field, InitVar
from enum import Enum

logger = logging.getLogger(__name__)

class McpTransportType(str, Enum):
    """Enumeration of supported MCP transport types."""
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"
    WEBSOCKET = "websocket"

@dataclass(frozen=True)
class McpServerInstanceKey:
    """
    A dedicated, hashable key for identifying a unique server instance.
    An instance is unique for a given agent and a specific server configuration.
    """
    agent_id: str
    server_id: str

@dataclass
class BaseMcpConfig:
    """
    Base configuration for an MCP server.
    The `server_id` attribute serves as a unique identifier for this specific
    MCP server configuration.
    """
    server_id: str 
    transport_type: McpTransportType = field(init=False) # Will be set by subclasses
    enabled: bool = True
    tool_name_prefix: Optional[str] = None

    def __post_init__(self):
        if not self.server_id or not isinstance(self.server_id, str): 
            raise ValueError(f"{self.__class__.__name__} 'server_id' must be a non-empty string.") 
        if not isinstance(self.enabled, bool):
            raise ValueError(f"{self.__class__.__name__} 'enabled' for server '{self.server_id}' must be a boolean.") 
        if self.tool_name_prefix is not None and not isinstance(self.tool_name_prefix, str):
            raise ValueError(f"{self.__class__.__name__} 'tool_name_prefix' for server '{self.server_id}' must be a string if provided.") 

@dataclass
class StdioMcpServerConfig(BaseMcpConfig):
    """Configuration parameters for an MCP server using stdio transport."""
    command: Optional[str] = None # Changed: Added default None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__() 
        self.transport_type = McpTransportType.STDIO

        # BUG FIX: Normalize cwd. An empty string is invalid for subprocess creation
        # and should be treated as None (use parent CWD).
        if self.cwd == '':
            self.cwd = None

        if self.command is None or not isinstance(self.command, str) or not self.command.strip():
            raise ValueError(f"StdioMcpServerConfig '{self.server_id}' 'command' must be a non-empty string.")
        
        if not isinstance(self.args, list) or not all(isinstance(arg, str) for arg in self.args):
            raise ValueError(f"StdioMcpServerConfig '{self.server_id}' 'args' must be a list of strings.") 
        if not isinstance(self.env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in self.env.items()):
            raise ValueError(f"StdioMcpServerConfig '{self.server_id}' 'env' must be a Dict[str, str].") 
        if self.cwd is not None and not isinstance(self.cwd, str):
            raise ValueError(f"StdioMcpServerConfig '{self.server_id}' 'cwd' must be a string if provided.") 

@dataclass
class StreamableHttpMcpServerConfig(BaseMcpConfig):
    """Configuration parameters for an MCP server using Streamable HTTP transport."""
    url: Optional[str] = None # Changed: Added default None
    token: Optional[str] = None 
    headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.transport_type = McpTransportType.STREAMABLE_HTTP

        if self.url is None or not isinstance(self.url, str) or not self.url.strip():
            raise ValueError(f"StreamableHttpMcpServerConfig '{self.server_id}' 'url' must be a non-empty string.")
        
        if self.token is not None and not isinstance(self.token, str):
            raise ValueError(f"StreamableHttpMcpServerConfig '{self.server_id}' 'token' must be a string if provided.") 
        if not isinstance(self.headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in self.headers.items()):
            raise ValueError(f"StreamableHttpMcpServerConfig '{self.server_id}' 'headers' must be a Dict[str, str].")

@dataclass
class WebsocketMcpServerConfig(BaseMcpConfig):
    """Configuration parameters for an MCP server using a WebSocket transport."""

    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    subprotocols: List[str] = field(default_factory=list)
    origin: Optional[str] = None
    open_timeout: Optional[float] = 10.0
    ping_interval: Optional[float] = None
    ping_timeout: Optional[float] = None
    verify_tls: bool = True
    ca_file: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.transport_type = McpTransportType.WEBSOCKET

        if self.url is None or not isinstance(self.url, str) or not self.url.strip():
            raise ValueError(f"WebsocketMcpServerConfig '{self.server_id}' 'url' must be a non-empty string.")

        normalized_url = self.url.strip().lower()
        if not (normalized_url.startswith("ws://") or normalized_url.startswith("wss://")):
            raise ValueError(
                f"WebsocketMcpServerConfig '{self.server_id}' 'url' must start with ws:// or wss://."
            )

        if not isinstance(self.headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in self.headers.items()):
            raise ValueError(f"WebsocketMcpServerConfig '{self.server_id}' 'headers' must be a Dict[str, str].")

        if not isinstance(self.subprotocols, list) or not all(isinstance(item, str) for item in self.subprotocols):
            raise ValueError(f"WebsocketMcpServerConfig '{self.server_id}' 'subprotocols' must be a list of strings.")

        if self.origin is not None and not isinstance(self.origin, str):
            raise ValueError(f"WebsocketMcpServerConfig '{self.server_id}' 'origin' must be a string if provided.")

        for field_name in ("open_timeout", "ping_interval", "ping_timeout"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, (int, float)) or value <= 0):
                raise ValueError(
                    f"WebsocketMcpServerConfig '{self.server_id}' '{field_name}' must be a positive number when provided."
                )

        if not isinstance(self.verify_tls, bool):
            raise ValueError(f"WebsocketMcpServerConfig '{self.server_id}' 'verify_tls' must be a boolean.")

        for path_field in ("ca_file", "client_cert", "client_key"):
            path_value = getattr(self, path_field)
            if path_value is not None and not isinstance(path_value, str):
                raise ValueError(
                    f"WebsocketMcpServerConfig '{self.server_id}' '{path_field}' must be a string path when provided."
                )

        if self.client_key and not self.client_cert:
            raise ValueError(
                f"WebsocketMcpServerConfig '{self.server_id}' requires 'client_cert' when 'client_key' is provided."
            )
