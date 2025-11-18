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
    StreamableHttpMcpServerConfig,
    WebsocketMcpServerConfig,
    BaseMcpConfig
)

# Test Data: Using 'server_id' as key, and nested 'stdio_params', 'streamable_http_params' etc.
# The McpConfigService is now expected to un-nest these.

USER_EXAMPLE_1_DICT_OF_DICTS = {
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

VALID_WEBSOCKET_CONFIG_LIST_ITEM = {
    "server_id": "ws_server_1",
    "transport_type": "websocket",
    "enabled": True,
    "tool_name_prefix": "ws_",
    "websocket_params": {
        "url": "wss://localhost:8765/mcp",
        "headers": {"X-Test": "1"},
        "subprotocols": ["custom"],
        "open_timeout": 5,
        "ping_interval": 15,
        "verify_tls": False,
    }
}


@pytest.fixture
def mcp_config_service() -> McpConfigService:
    # Use a new instance for each test to ensure isolation
    if McpConfigService in McpConfigService._instances:
        del McpConfigService._instances[McpConfigService]
    service = McpConfigService()
    # Clear any potential state from other tests if singleton is not fully isolated by pytest runs
    service.clear_configs()
    return service

def test_load_config_from_dict(mcp_config_service: McpConfigService):
    """Tests loading a single config from a dictionary."""
    config_dict_to_load = {"stdio_server_1": {"transport_type": "stdio", "command": "python"}}
    
    loaded_config = mcp_config_service.load_config_from_dict(config_dict_to_load)
    assert isinstance(loaded_config, StdioMcpServerConfig)
    assert loaded_config.server_id == "stdio_server_1"
    
    stored_config = mcp_config_service.get_config("stdio_server_1")
    assert stored_config is not None
    assert stored_config.command == "python"
    assert len(mcp_config_service.get_all_configs()) == 1

def test_load_configs_from_dict(mcp_config_service: McpConfigService):
    """Tests loading multiple configs from a dictionary of dictionaries."""
    configs_data = {
        "stdio_server_1": VALID_STDIO_CONFIG_LIST_ITEM,
        "http_server_1": VALID_HTTP_CONFIG_LIST_ITEM,
        "ws_server_1": VALID_WEBSOCKET_CONFIG_LIST_ITEM,
    }
    loaded = mcp_config_service.load_configs_from_dict(configs_data)
    assert len(loaded) == 3
    assert len(mcp_config_service.get_all_configs()) == 3
    
    config1 = mcp_config_service.get_config("stdio_server_1")
    assert isinstance(config1, StdioMcpServerConfig)
    assert config1.command == "python"

    config2 = mcp_config_service.get_config("http_server_1")
    assert isinstance(config2, StreamableHttpMcpServerConfig)
    assert config2.url == "http://localhost:9000/stream"

    config3 = mcp_config_service.get_config("ws_server_1")
    assert isinstance(config3, WebsocketMcpServerConfig)
    assert config3.url == "wss://localhost:8765/mcp"

def test_load_configs_from_file_with_list(mcp_config_service: McpConfigService, tmp_path):
    """Tests loading from a JSON file containing a list of configs."""
    file_content = [
        VALID_STDIO_CONFIG_LIST_ITEM,
        VALID_HTTP_CONFIG_LIST_ITEM,
        VALID_WEBSOCKET_CONFIG_LIST_ITEM,
    ]
    config_file = tmp_path / "mcp_config_list.json"
    config_file.write_text(json.dumps(file_content))

    loaded = mcp_config_service.load_configs_from_file(str(config_file))
    assert len(loaded) == 3
    
    stdio_conf = mcp_config_service.get_config("stdio_server_1")
    assert isinstance(stdio_conf, StdioMcpServerConfig)
    assert stdio_conf.command == "python"

    http_conf = mcp_config_service.get_config("http_server_1")
    assert isinstance(http_conf, StreamableHttpMcpServerConfig)
    assert http_conf.url == "http://localhost:9000/stream"

    ws_conf = mcp_config_service.get_config("ws_server_1")
    assert isinstance(ws_conf, WebsocketMcpServerConfig)
    assert ws_conf.url == "wss://localhost:8765/mcp"

def test_load_configs_from_file_with_dict(mcp_config_service: McpConfigService, tmp_path):
    """Tests loading from a JSON file containing a dictionary of configs."""
    file_content = USER_EXAMPLE_1_DICT_OF_DICTS
    config_file = tmp_path / "mcp_config_dict.json"
    config_file.write_text(json.dumps(file_content))
    
    loaded = mcp_config_service.load_configs_from_file(str(config_file))
    assert len(loaded) == 1
    config = mcp_config_service.get_config("google-slides-mcp")
    assert isinstance(config, StdioMcpServerConfig)
    assert config.command == "node"

@pytest.mark.parametrize("invalid_data, error_message_match, method_name", [
    ([{"transport_type": "stdio"}], "each item must be a dict with a 'server_id'", "load_configs_from_file"),
    ({"myid": {"transport_type": "invalid_type"}}, "Invalid 'transport_type' string 'invalid_type'", "load_configs_from_dict"),
    ({"myid": {"transport_type": "stdio", "stdio_params": {"command": 123}}}, "incompatible parameters for STDIO config", "load_configs_from_dict"),
    ({"myid": {"transport_type": "streamable_http", "streamable_http_params": {}}}, "incompatible parameters for STREAMABLE_HTTP config", "load_configs_from_dict"),
    ({"myid": {"transport_type": "websocket", "websocket_params": {}}}, "WebsocketMcpServerConfig 'myid' 'url' must be a non-empty string", "load_configs_from_dict"),
])
def test_load_configs_invalid_data_raises_value_error(mcp_config_service: McpConfigService, invalid_data, error_message_match, method_name, tmp_path):
    with pytest.raises(ValueError, match=error_message_match):
        if method_name == "load_configs_from_file":
            config_file = tmp_path / "invalid.json"
            config_file.write_text(json.dumps(invalid_data))
            mcp_config_service.load_configs_from_file(str(config_file))
        else:
             mcp_config_service.load_configs_from_dict(invalid_data) # type: ignore

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

def test_remove_config(mcp_config_service: McpConfigService):
    """Tests the new remove_config method."""
    config_dict = {"server_to_remove": {"transport_type": "stdio", "command": "mycmd"}}
    mcp_config_service.load_config_from_dict(config_dict)
    
    # Verify it's there
    assert mcp_config_service.get_config("server_to_remove") is not None
    
    # Remove and verify it's gone
    result = mcp_config_service.remove_config("server_to_remove")
    assert result is True
    assert mcp_config_service.get_config("server_to_remove") is None
    
    # Test removing a non-existent config
    result_nonexistent = mcp_config_service.remove_config("nonexistent_server")
    assert result_nonexistent is False

def test_clear_configs(mcp_config_service: McpConfigService):
    mcp_config_service.load_config_from_dict({"server1": {"transport_type": "stdio", "command": "c"}})
    assert len(mcp_config_service.get_all_configs()) == 1
    mcp_config_service.clear_configs()
    assert len(mcp_config_service.get_all_configs()) == 0
