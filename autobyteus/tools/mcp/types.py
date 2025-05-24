# file: autobyteus/autobyteus/mcp/types.py
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class McpTransportType(str, Enum):
    """Enumeration of supported MCP transport types."""
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"

@dataclass
class StdioServerParametersConfig:
    """Configuration parameters for an MCP server using stdio transport."""
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None

    def __post_init__(self):
        if not self.command or not isinstance(self.command, str):
            raise ValueError("StdioServerParametersConfig 'command' must be a non-empty string.")
        if not isinstance(self.args, list) or not all(isinstance(arg, str) for arg in self.args):
            raise ValueError("StdioServerParametersConfig 'args' must be a list of strings.")
        if not isinstance(self.env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in self.env.items()):
            raise ValueError("StdioServerParametersConfig 'env' must be a Dict[str, str].")
        if self.cwd is not None and not isinstance(self.cwd, str):
            raise ValueError("StdioServerParametersConfig 'cwd' must be a string if provided.")

@dataclass
class SseTransportConfig:
    """Configuration parameters for an MCP server using SSE transport."""
    url: str
    token: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.url or not isinstance(self.url, str):
            raise ValueError("SseTransportConfig 'url' must be a non-empty string.")
        if self.token is not None and not isinstance(self.token, str):
            raise ValueError("SseTransportConfig 'token' must be a string if provided.")
        if not isinstance(self.headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in self.headers.items()):
            raise ValueError("SseTransportConfig 'headers' must be a Dict[str, str].")

@dataclass
class StreamableHttpConfig:
    """Configuration parameters for an MCP server using Streamable HTTP transport."""
    url: str
    # Assuming similar parameters to SSE for now, like token and headers
    token: Optional[str] = None # Example: for bearer token authentication
    headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.url or not isinstance(self.url, str):
            raise ValueError("StreamableHttpConfig 'url' must be a non-empty string.")
        if self.token is not None and not isinstance(self.token, str):
            raise ValueError("StreamableHttpConfig 'token' must be a string if provided.")
        if not isinstance(self.headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in self.headers.items()):
            raise ValueError("StreamableHttpConfig 'headers' must be a Dict[str, str].")

@dataclass
class McpConfig:
    """
    Configuration for a single MCP server.
    The `server_name` attribute serves as a unique identifier for this specific
    MCP server configuration (e.g., "google_slides_mcp_server", "local_calculator_mcp").
    It's used as the key in configuration maps and for retrieving specific server settings.
    """
    server_name: str  # RENAMED from 'id'. This is the unique name/identifier for the server config.
    transport_type: McpTransportType
    enabled: bool = True
    tool_name_prefix: Optional[str] = None
    stdio_params: Optional[StdioServerParametersConfig] = None
    sse_params: Optional[SseTransportConfig] = None
    streamable_http_params: Optional[StreamableHttpConfig] = None

    def __post_init__(self):
        if not self.server_name or not isinstance(self.server_name, str): # UPDATED field name and error message
            raise ValueError("McpConfig 'server_name' must be a non-empty string.")

        if isinstance(self.transport_type, str):
            try:
                self.transport_type = McpTransportType(self.transport_type.lower())
            except ValueError:
                valid_types = [t.value for t in McpTransportType]
                raise ValueError(f"McpConfig 'transport_type' string '{self.transport_type}' is not a valid McpTransportType. Valid types are: {valid_types}.")
        elif not isinstance(self.transport_type, McpTransportType):
             raise TypeError(f"McpConfig 'transport_type' must be a McpTransportType enum or a valid string. Got {type(self.transport_type)}")

        if self.transport_type == McpTransportType.STDIO and self.stdio_params is None:
            raise ValueError("McpConfig with transport_type 'stdio' requires 'stdio_params'.")
        if self.transport_type == McpTransportType.SSE and self.sse_params is None:
            raise ValueError("McpConfig with transport_type 'sse' requires 'sse_params'.")
        if self.transport_type == McpTransportType.STREAMABLE_HTTP and self.streamable_http_params is None:
            raise ValueError("McpConfig with transport_type 'streamable_http' requires 'streamable_http_params'.")

        # Update error messages to refer to server_name if they used self.id
        if self.stdio_params is not None and not isinstance(self.stdio_params, StdioServerParametersConfig):
            if isinstance(self.stdio_params, dict):
                try:
                    self.stdio_params = StdioServerParametersConfig(**self.stdio_params)
                except Exception as e:
                    raise ValueError(f"Failed to parse 'stdio_params' dictionary for McpConfig '{self.server_name}': {e}") from e # UPDATED
            else:
                raise TypeError(f"McpConfig '{self.server_name}' field 'stdio_params' must be an instance of StdioServerParametersConfig or a compatible dict.") # UPDATED

        if self.sse_params is not None and not isinstance(self.sse_params, SseTransportConfig):
            if isinstance(self.sse_params, dict):
                try:
                    self.sse_params = SseTransportConfig(**self.sse_params)
                except Exception as e:
                    raise ValueError(f"Failed to parse 'sse_params' dictionary for McpConfig '{self.server_name}': {e}") from e # UPDATED
            else:
                raise TypeError(f"McpConfig '{self.server_name}' field 'sse_params' must be an instance of SseTransportConfig or a compatible dict.") # UPDATED

        if self.streamable_http_params is not None and not isinstance(self.streamable_http_params, StreamableHttpConfig):
            if isinstance(self.streamable_http_params, dict):
                try:
                    self.streamable_http_params = StreamableHttpConfig(**self.streamable_http_params)
                except Exception as e:
                    raise ValueError(f"Failed to parse 'streamable_http_params' dictionary for McpConfig '{self.server_name}': {e}") from e # UPDATED
            else:
                raise TypeError(f"McpConfig '{self.server_name}' field 'streamable_http_params' must be an instance of StreamableHttpConfig or a compatible dict.") # UPDATED

        if self.tool_name_prefix is not None and not isinstance(self.tool_name_prefix, str):
            raise ValueError("McpConfig 'tool_name_prefix' must be a string if provided.")
