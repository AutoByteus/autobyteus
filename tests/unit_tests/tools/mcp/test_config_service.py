# file: autobyteus/tests/unit_tests/tools/mcp/test_config_service.py
import pytest
import json
import os
from typing import List, Dict, Any

# Updated import path
from autobyteus.tools.mcp import (
    McpConfigService,
    McpTransportType,
    StdioMcpServerConfig,
    SseMcpServerConfig,
    StreamableHttpMcpServerConfig,
    BaseMcpConfig
)

# Test Data: Using 'server_id' as key, and nested 'stdio_params', 'sse_params' etc.
# The McpConfigService is now expected to un-nest these.

USER_EXAMPLE_1_FLAT_DICT_AS_INPUT = {
    "google-slides-mcp": { # This key is the server_id
        "transport_type": "stdio",
        "enabled": True,
        "stdio_params": {
            "command": "node",
            "args": ["/path/to/google-slides-mcp/build/index.js"],
            "env": {
                "GOOGLE_CLIENT_ID": "YOUR_CLIENT_ID",
                "GOOGLE_CLIENT_SECRET": "YOUR_CLIENT_SECRET",
                "GOOGLE_REFRESH_TOKEN": "YOUR_REFRESH_TOKEN"
            }
        }
    }
}

VALID_STDIO_SINGLE_CONFIG_DICT = {
    "server_id": "stdio_server_1",
    "transport_type": "stdio",
    "stdio_params": {"command": "python"}
}


VALID_STDIO_CONFIG_LIST_ITEM = {
    "server_id": "stdio_server_1",
    "transport_type": "stdio",
    "enabled": True,
    "tool_name_prefix": "std_",
    "stdio_params": {
        "command": "python",
        "args": ["-m", "my_mcp_server"],
        "env": {"PYTHONUNBUFFERED": "1"},
        "cwd": "/tmp"
    }
}

VALID_SSE_CONFIG_LIST_ITEM = {
    "server_id": "sse_server_1",
    "transport_type": "sse",
    "enabled": False,
    "tool_name_prefix": "sse_remote_",
    "sse_params": {
        "url": "http://localhost:8000/events",
        "token": "secret-token",
        "headers": {"X-Custom-Header": "value"}
    }
}

VALID_HTTP_CONFIG_LIST_ITEM = {
    "server_id": "http_server_1",
    "transport_type": "streamable_http",
    "enabled": True,
    "tool_name_prefix": "http_",
    "streamable_http_params": {
        "url": "http://localhost:9000/stream",
        "token": "http-secret-token",
        "headers": {"X-Http-Header": "http_value"}
    }
}


@pytest.fixture
def mcp_config_service() -> McpConfigService:
    # Use a new instance for each test to ensure isolation
    service = McpConfigService()
    # Clear any potential state from other tests if singleton is not fully isolated by pytest runs
    service.clear_configs()
    return service

def test_load_config_singular(mcp_config_service: McpConfigService):
    """Tests the new singular load_config method."""
    config_dict_to_load = {"stdio_server_1": {"transport_type": "stdio", "command": "python"}}
    
    loaded_config = mcp_config_service.load_config(config_dict_to_load)
    assert isinstance(loaded_config, StdioMcpServerConfig)
    assert loaded_config.server_id == "stdio_server_1"
    
    stored_config = mcp_config_service.get_config("stdio_server_1")
    assert stored_config is not None
    assert stored_config.command == "python"
    assert len(mcp_config_service.get_all_configs()) == 1

def test_load_configs_plural_from_list(mcp_config_service: McpConfigService):
    configs_data = [VALID_STDIO_CONFIG_LIST_ITEM, VALID_SSE_CONFIG_LIST_ITEM]
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 2
    assert len(mcp_config_service.get_all_configs()) == 2
    
    config1 = mcp_config_service.get_config("stdio_server_1")
    assert isinstance(config1, StdioMcpServerConfig)
    assert config1.command == "python"

    config2 = mcp_config_service.get_config("sse_server_1")
    assert isinstance(config2, SseMcpServerConfig)
    assert config2.url == "http://localhost:8000/events"

def test_load_configs_plural_from_dict_of_dicts(mcp_config_service: McpConfigService):
    configs_data = USER_EXAMPLE_1_FLAT_DICT_AS_INPUT
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 1
    config = mcp_config_service.get_config("google-slides-mcp")
    assert isinstance(config, StdioMcpServerConfig)
    assert config.command == "node"


def test_load_configs_from_file(mcp_config_service: McpConfigService, tmp_path):
    file_content = [VALID_STDIO_CONFIG_LIST_ITEM, VALID_SSE_CONFIG_LIST_ITEM]
    config_file = tmp_path / "mcp_config_list.json"
    config_file.write_text(json.dumps(file_content))

    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 2
    
    stdio_conf = mcp_config_service.get_config("stdio_server_1")
    assert isinstance(stdio_conf, StdioMcpServerConfig)
    assert stdio_conf.command == "python"

    sse_conf = mcp_config_service.get_config("sse_server_1")
    assert isinstance(sse_conf, SseMcpServerConfig)
    assert sse_conf.url == "http://localhost:8000/events"

@pytest.mark.parametrize("invalid_data, error_message_match", [
    ([{"transport_type": "stdio"}], "missing 'server_id' field"),
    ({"myid": {"transport_type": "invalid_type"}}, "Invalid 'transport_type' string 'invalid_type'"),
    ({"myid": {"transport_type": "stdio", "stdio_params": {"command": 123}}}, "incompatible parameters for STDIO config"),
    ({"myid": {"transport_type": "sse", "sse_params": {"url": None}}}, "incompatible parameters for SSE config"),
    ({"myid": {"transport_type": "streamable_http", "streamable_http_params": {}}}, "incompatible parameters for STREAMABLE_HTTP config"),
])
def test_load_configs_invalid_data_raises_value_error(mcp_config_service: McpConfigService, invalid_data, error_message_match):
    with pytest.raises(ValueError, match=error_message_match):
        mcp_config_service.load_configs(invalid_data)

def test_load_configs_unsupported_source_type(mcp_config_service: McpConfigService):
    with pytest.raises(TypeError, match="Unsupported source type"):
        mcp_config_service.load_configs(123) # type: ignore

def test_add_config(mcp_config_service: McpConfigService):
    stdio_obj = StdioMcpServerConfig(
        server_id="google-doc-mcp",
        command="node",
        args=["/path/to/google-doc-mcp/index.js"],
    )
    
    returned_config = mcp_config_service.add_config(stdio_obj)
    assert returned_config == stdio_obj
    assert mcp_config_service.get_config("google-doc-mcp") == stdio_obj

def test_add_config_overwrites(mcp_config_service: McpConfigService, caplog):
    config_v1_obj = StdioMcpServerConfig(server_id="common_server", command="cmd_v1")
    config_v2_obj = StdioMcpServerConfig(server_id="common_server", command="cmd_v2")

    mcp_config_service.add_config(config_v1_obj)
    mcp_config_service.add_config(config_v2_obj)
    
    assert "Overwriting existing MCP config with server_id 'common_server'" in caplog.text 
    stored_config = mcp_config_service.get_config("common_server")
    assert stored_config.command == "cmd_v2"

def test_clear_configs(mcp_config_service: McpConfigService):
    mcp_config_service.load_config({"server1": {"transport_type": "stdio", "command": "c"}})
    assert len(mcp_config_service.get_all_configs()) == 1
    mcp_config_service.clear_configs()
    assert len(mcp_config_service.get_all_configs()) == 0
