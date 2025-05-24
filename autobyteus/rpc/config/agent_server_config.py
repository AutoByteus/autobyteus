# file: autobyteus/autobyteus/rpc/config/agent_server_config.py
import logging
from typing import Optional, Dict, Any, List # List was missing
from pydantic import BaseModel, Field, validator, HttpUrl

from autobyteus.rpc.transport_type import TransportType

logger = logging.getLogger(__name__)

class AgentServerConfig(BaseModel):
    """
    Configuration for an Agent Server, specifying how it can be connected to.
    """
    server_id: str = Field(..., description="Unique identifier for this server configuration.")
    transport_type: TransportType = Field(..., description="The transport mechanism (e.g., stdio, sse).")
    
    # For stdio transport
    stdio_command: Optional[List[str]] = Field(default=None, description="Command and arguments to launch the agent server process for stdio.")
    
    # For sse transport
    sse_base_url: Optional[HttpUrl] = Field(default=None, description="Base URL for the agent server's HTTP/SSE endpoints.")
    sse_request_endpoint: str = Field(default="/invoke", description="Relative path for synchronous requests (e.g., invoke_method).")
    sse_events_endpoint: str = Field(default="/events", description="Relative path for the Server-Sent Events stream.")
    # New field for HTTP stream downloads
    sse_stream_download_path_prefix: str = Field(default="/streams", description="Base relative path for HTTP stream downloads. Full path will be {base_url}{prefix}/{agent_id_on_server}/{stream_id}.")


    # Optional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata for the server configuration.")

    class Config:
        use_enum_values = True # Serialize enums to their values
        validate_assignment = True

    @validator('stdio_command')
    def _check_stdio_command(cls, v, values):
        if values.get('transport_type') == TransportType.STDIO and not v:
            raise ValueError("stdio_command is required for stdio transport type.")
        if values.get('transport_type') != TransportType.STDIO and v:
            logger.warning("stdio_command is provided but transport_type is not stdio. It will be ignored.")
        return v

    @validator('sse_base_url')
    def _check_sse_base_url(cls, v, values):
        if values.get('transport_type') == TransportType.SSE and not v:
            raise ValueError("sse_base_url is required for sse transport type.")
        if values.get('transport_type') != TransportType.SSE and v:
            logger.warning("sse_base_url is provided but transport_type is not sse. It will be ignored.")
        return v
    
    @validator('sse_stream_download_path_prefix')
    def _check_sse_stream_download_path_prefix(cls, v, values):
        if not v.startswith('/'):
            raise ValueError("sse_stream_download_path_prefix must start with a '/'.")
        if values.get('transport_type') != TransportType.SSE and v != "/streams": # if not default and not SSE
             logger.warning("sse_stream_download_path_prefix is customized but transport_type is not sse. It might be ignored.")
        return v


    def get_sse_full_request_url(self) -> Optional[str]:
        """Returns the full URL for SSE synchronous requests if applicable."""
        if self.transport_type == TransportType.SSE and self.sse_base_url:
            # Pydantic's HttpUrl converts to string automatically when concatenated this way
            return str(self.sse_base_url).rstrip('/') + self.sse_request_endpoint
        return None

    def get_sse_full_events_url(self) -> Optional[str]:
        """Returns the full URL for the SSE event stream if applicable."""
        if self.transport_type == TransportType.SSE and self.sse_base_url:
            return str(self.sse_base_url).rstrip('/') + self.sse_events_endpoint
        return None

    def get_sse_full_stream_download_url_prefix_for_agent(self, agent_id_on_server: str) -> Optional[str]:
        """
        Returns the full URL prefix for HTTP stream downloads for a specific agent,
        up to the point where stream_id should be appended.
        e.g., http://host:port/streams/{agent_id_on_server}
        """
        if self.transport_type == TransportType.SSE and self.sse_base_url:
            base = str(self.sse_base_url).rstrip('/')
            prefix = self.sse_stream_download_path_prefix.rstrip('/')
            return f"{base}{prefix}/{agent_id_on_server}"
        return None


    def __repr__(self) -> str:
        return f"<AgentServerConfig server_id='{self.server_id}', transport='{self.transport_type.value}'>"

if __name__ == "__main__": # pragma: no cover
    logging.basicConfig(level=logging.DEBUG)

    # Stdio Example
    try:
        stdio_config_data = {
            "server_id": "local_agent_stdio",
            "transport_type": "stdio",
            "stdio_command": ["python", "-m", "autobyteus.agent.server_main", "--config-id", "local_agent_stdio"]
        }
        stdio_config = AgentServerConfig(**stdio_config_data)
        logger.info(f"Stdio Config: {stdio_config!r}")
        logger.info(f"Stdio Config (dict): {stdio_config.model_dump_json(indent=2)}")
    except ValueError as e:
        logger.error(f"Error creating stdio_config: {e}")

    # SSE Example
    try:
        sse_config_data = {
            "server_id": "remote_agent_sse",
            "transport_type": "sse",
            "sse_base_url": "http://localhost:8000/agent1",
            "sse_request_endpoint": "/api/request",
            "sse_events_endpoint": "/api/events",
            "sse_stream_download_path_prefix": "/downloadable_content" # Custom prefix
        }
        sse_config = AgentServerConfig(**sse_config_data)
        logger.info(f"SSE Config: {sse_config!r}")
        logger.info(f"SSE Config (dict): {sse_config.model_dump_json(indent=2)}")
        logger.info(f"SSE Request URL: {sse_config.get_sse_full_request_url()}")
        logger.info(f"SSE Events URL: {sse_config.get_sse_full_events_url()}")
        logger.info(f"SSE Stream Download URL prefix for agent 'test_agent': {sse_config.get_sse_full_stream_download_url_prefix_for_agent('test_agent')}")
        
        # Test HttpUrl string conversion
        assert isinstance(sse_config.sse_base_url, HttpUrl)
        logger.info(f"SSE base URL type: {type(sse_config.sse_base_url)}, value: {sse_config.sse_base_url}")

    except ValueError as e:
        logger.error(f"Error creating sse_config: {e}")

    # Validation error examples
    try:
        invalid_stdio_data = {"server_id": "invalid_stdio", "transport_type": "stdio"} # Missing stdio_command
        AgentServerConfig(**invalid_stdio_data)
    except ValueError as e:
        logger.error(f"Expected validation error (stdio): {e}")

    try:
        invalid_sse_data = {"server_id": "invalid_sse", "transport_type": "sse"} # Missing sse_base_url
        AgentServerConfig(**invalid_sse_data)
    except ValueError as e:
        logger.error(f"Expected validation error (sse): {e}")
        
    try:
        invalid_url_sse_data = {"server_id": "invalid_url_sse", "transport_type": "sse", "sse_base_url": "not_a_url"}
        AgentServerConfig(**invalid_url_sse_data)
    except ValueError as e:
        logger.error(f"Expected validation error (invalid sse_base_url): {e}")
    
    try:
        invalid_stream_prefix = {"server_id": "invalid_stream_prefix", "transport_type": "sse", "sse_base_url":"http://foo.com", "sse_stream_download_path_prefix": "no_slash_prefix"}
        AgentServerConfig(**invalid_stream_prefix)
    except ValueError as e:
        logger.error(f"Expected validation error (invalid sse_stream_download_path_prefix): {e}")

