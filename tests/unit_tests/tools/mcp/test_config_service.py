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

USER_EXAMPLE_2_FLAT_DICT_AS_INPUT = {
    "google-maps": {
        "transport_type": "stdio",
        "enabled": True,
        "stdio_params": {
            "command": "docker",
            "args": ["run", "-i", "--rm", "-e", "GOOGLE_MAPS_API_KEY", "mcp/google-maps"],
            "env": {"GOOGLE_MAPS_API_KEY": "<YOUR_API_KEY>"}
        }
    }
}

USER_EXAMPLE_3_FLAT_DICT_AS_INPUT = {
    "live-collab-mcp": {
        "transport_type": "sse",
        "enabled": True,
        "sse_params": {
            "url": "https://live-collab.example.com/api/v1/events"
        }
    }
}

USER_EXAMPLE_4_FLAT_DICT_AS_INPUT = {
    "mcp-deepwiki": {
        "transport_type": "stdio",
        "stdio_params": {
            "command": "npx",
            "args": ["-y", "mcp-deepwiki@latest"]
        }
        # enabled defaults to True
    }
}

VALID_STDIO_CONFIG_LIST_ITEM = {
    "server_id": "stdio_server_1", # Changed from server_name
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
    "server_id": "sse_server_1", # Changed from server_name
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
    return McpConfigService()

def test_load_configs_from_list_valid_stdio(mcp_config_service: McpConfigService):
    configs_data = [VALID_STDIO_CONFIG_LIST_ITEM]
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 1
    assert len(mcp_config_service.get_all_configs()) == 1
    
    config = mcp_config_service.get_config("stdio_server_1")
    assert isinstance(config, StdioMcpServerConfig)
    assert config.server_id == "stdio_server_1"
    assert config.transport_type == McpTransportType.STDIO
    assert config.enabled is True
    assert config.tool_name_prefix == "std_"
    assert config.command == "python"
    assert config.args == ["-m", "my_mcp_server"]
    assert config.env == {"PYTHONUNBUFFERED": "1"}
    assert config.cwd == "/tmp"

def test_load_configs_from_list_valid_sse(mcp_config_service: McpConfigService):
    configs_data = [VALID_SSE_CONFIG_LIST_ITEM]
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 1
    config = mcp_config_service.get_config("sse_server_1")
    assert isinstance(config, SseMcpServerConfig)
    assert config.server_id == "sse_server_1"
    assert config.transport_type == McpTransportType.SSE
    assert config.enabled is False
    assert config.tool_name_prefix == "sse_remote_"
    assert config.url == "http://localhost:8000/events"
    assert config.token == "secret-token"
    assert config.headers == {"X-Custom-Header": "value"}

def test_load_configs_from_list_valid_http(mcp_config_service: McpConfigService):
    configs_data = [VALID_HTTP_CONFIG_LIST_ITEM]
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 1
    config = mcp_config_service.get_config("http_server_1")
    assert isinstance(config, StreamableHttpMcpServerConfig)
    assert config.server_id == "http_server_1"
    assert config.transport_type == McpTransportType.STREAMABLE_HTTP
    assert config.enabled is True
    assert config.tool_name_prefix == "http_"
    assert config.url == "http://localhost:9000/stream"
    assert config.token == "http-secret-token"
    assert config.headers == {"X-Http-Header": "http_value"}


def test_load_configs_from_list_mixed(mcp_config_service: McpConfigService):
    configs_data = [VALID_STDIO_CONFIG_LIST_ITEM, VALID_SSE_CONFIG_LIST_ITEM, VALID_HTTP_CONFIG_LIST_ITEM]
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 3
    assert len(mcp_config_service.get_all_configs()) == 3
    assert mcp_config_service.get_config("stdio_server_1") is not None
    assert mcp_config_service.get_config("sse_server_1") is not None
    assert mcp_config_service.get_config("http_server_1") is not None

def test_load_configs_from_file_list_format(mcp_config_service: McpConfigService, tmp_path):
    file_content = [VALID_STDIO_CONFIG_LIST_ITEM, VALID_SSE_CONFIG_LIST_ITEM]
    config_file = tmp_path / "mcp_config_list.json"
    config_file.write_text(json.dumps(file_content))

    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 2
    # Check specific attributes after loading
    stdio_conf = mcp_config_service.get_config("stdio_server_1")
    assert isinstance(stdio_conf, StdioMcpServerConfig)
    assert stdio_conf.command == "python"

    sse_conf = mcp_config_service.get_config("sse_server_1")
    assert isinstance(sse_conf, SseMcpServerConfig)
    assert sse_conf.url == "http://localhost:8000/events"


def test_load_configs_from_file_dict_format_user_example1(mcp_config_service: McpConfigService, tmp_path):
    config_file = tmp_path / "mcp_config_ex1.json"
    config_file.write_text(json.dumps(USER_EXAMPLE_1_FLAT_DICT_AS_INPUT))
    
    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 1
    config = mcp_config_service.get_config("google-slides-mcp")
    assert isinstance(config, StdioMcpServerConfig)
    assert config.server_id == "google-slides-mcp"
    assert config.transport_type == McpTransportType.STDIO
    assert config.command == "node"
    assert config.env["GOOGLE_CLIENT_ID"] == "YOUR_CLIENT_ID"

def test_load_configs_from_file_dict_format_user_example3_sse(mcp_config_service: McpConfigService, tmp_path):
    config_file = tmp_path / "mcp_config_ex3.json"
    config_file.write_text(json.dumps(USER_EXAMPLE_3_FLAT_DICT_AS_INPUT))

    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 1
    config = mcp_config_service.get_config("live-collab-mcp")
    assert isinstance(config, SseMcpServerConfig)
    assert config.server_id == "live-collab-mcp"
    assert config.transport_type == McpTransportType.SSE
    assert config.url == "https://live-collab.example.com/api/v1/events"

def test_load_configs_from_file_dict_format_user_example4_defaults(mcp_config_service: McpConfigService, tmp_path):
    config_file = tmp_path / "mcp_config_ex4.json"
    config_file.write_text(json.dumps(USER_EXAMPLE_4_FLAT_DICT_AS_INPUT))

    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 1
    config = mcp_config_service.get_config("mcp-deepwiki")
    assert isinstance(config, StdioMcpServerConfig)
    assert config.server_id == "mcp-deepwiki"
    assert config.transport_type == McpTransportType.STDIO
    assert config.command == "npx"
    assert config.enabled is True # Default from BaseMcpConfig
    assert config.env == {} # Default from StdioMcpServerConfig

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

def test_load_configs_invalid_json_file(mcp_config_service: McpConfigService, tmp_path):
    config_file = tmp_path / "invalid.json"
    config_file.write_text("this is not json")
    with pytest.raises(ValueError, match="Invalid JSON"):
        mcp_config_service.load_configs(str(config_file))

def test_load_configs_non_existent_file(mcp_config_service: McpConfigService):
    with pytest.raises(FileNotFoundError):
        mcp_config_service.load_configs("non_existent_file.json")
        
def test_load_configs_unsupported_source_type(mcp_config_service: McpConfigService):
    with pytest.raises(TypeError, match="Unsupported source type"):
        mcp_config_service.load_configs(123) # type: ignore

# Test add_config with pre-instantiated objects
def test_add_config_with_object_stdio(mcp_config_service: McpConfigService):
    stdio_obj = StdioMcpServerConfig(
        server_id="google-doc-mcp",
        enabled=True,
        tool_name_prefix="gdoc_",
        command="node",
        args=["/path/to/google-doc-mcp/index.js"],
        env={"API_KEY": "doc_api_key"}
    )
    
    returned_config = mcp_config_service.add_config(stdio_obj)
    assert returned_config == stdio_obj
    
    assert len(mcp_config_service.get_all_configs()) == 1
    stored_config = mcp_config_service.get_config("google-doc-mcp")
    assert isinstance(stored_config, StdioMcpServerConfig)
    assert stored_config.server_id == "google-doc-mcp"
    assert stored_config.command == "node"

def test_add_config_with_object_sse(mcp_config_service: McpConfigService):
    sse_obj = SseMcpServerConfig(
        server_id="google-calendar-mcp",
        enabled=True,
        url="https://calendar-mcp.example.com/api/events",
        token="cal_token_123",
        headers={"X-App-ID": "calendar_app"}
    )
    mcp_config_service.add_config(sse_obj)
    stored_config = mcp_config_service.get_config("google-calendar-mcp")
    assert isinstance(stored_config, SseMcpServerConfig)
    assert stored_config.url == "https://calendar-mcp.example.com/api/events"


def test_add_config_overwrites_existing_object(mcp_config_service: McpConfigService, caplog):
    config_v1_obj = StdioMcpServerConfig(server_id="common_server", command="cmd_v1")
    config_v2_obj = StdioMcpServerConfig(server_id="common_server", command="cmd_v2", enabled=False, args=["arg1"])

    mcp_config_service.add_config(config_v1_obj)
    stored_v1 = mcp_config_service.get_config("common_server")
    assert isinstance(stored_v1, StdioMcpServerConfig)
    assert stored_v1.command == "cmd_v1"
    assert stored_v1.enabled is True 

    caplog.clear()
    mcp_config_service.add_config(config_v2_obj)
    assert "Overwriting existing MCP config with server_id 'common_server'" in caplog.text 

    assert len(mcp_config_service.get_all_configs()) == 1
    stored_v2 = mcp_config_service.get_config("common_server")
    assert isinstance(stored_v2, StdioMcpServerConfig)
    assert stored_v2.command == "cmd_v2"
    assert stored_v2.args == ["arg1"]
    assert stored_v2.enabled is False

def test_add_config_with_unsupported_type_input(mcp_config_service: McpConfigService):
    with pytest.raises(TypeError, match="Unsupported input type for add_config"):
        mcp_config_service.add_config(12345) # type: ignore
    with pytest.raises(TypeError, match="Unsupported input type for add_config"):
        mcp_config_service.add_config([VALID_STDIO_CONFIG_LIST_ITEM]) # type: ignore


def test_get_config_non_existent(mcp_config_service: McpConfigService):
    assert mcp_config_service.get_config("non_existent_server_id") is None

def test_get_all_configs_empty(mcp_config_service: McpConfigService):
    assert mcp_config_service.get_all_configs() == []

def test_load_configs_duplicate_id_overwrites(mcp_config_service: McpConfigService, caplog):
    # Test with load_configs behavior for duplicates
    configs_data_v1 = [{"server_id": "server1", "transport_type": "stdio", "stdio_params": {"command": "cmd1"}}]
    configs_data_v2 = [{"server_id": "server1", "transport_type": "stdio", "stdio_params": {"command": "cmd2"}}]
    
    mcp_config_service.load_configs(configs_data_v1)
    conf_v1 = mcp_config_service.get_config("server1")
    assert isinstance(conf_v1, StdioMcpServerConfig)
    assert conf_v1.command == "cmd1"
    
    caplog.clear()
    mcp_config_service.load_configs(configs_data_v2)
    assert len(mcp_config_service.get_all_configs()) == 1
    conf_v2 = mcp_config_service.get_config("server1")
    assert isinstance(conf_v2, StdioMcpServerConfig)
    assert conf_v2.command == "cmd2"
    assert "Duplicate MCP config server_id 'server1' found" in caplog.text

def test_clear_configs(mcp_config_service: McpConfigService):
    mcp_config_service.load_configs([VALID_STDIO_CONFIG_LIST_ITEM])
    assert len(mcp_config_service.get_all_configs()) == 1
    mcp_config_service.clear_configs()
    assert len(mcp_config_service.get_all_configs()) == 0
    assert mcp_config_service.get_config(VALID_STDIO_CONFIG_LIST_ITEM["server_id"]) is None

# Tests for BaseMcpConfig and subclasses' __post_init__
def test_base_mcp_config_validation():
    with pytest.raises(ValueError, match="'server_id' must be a non-empty string"):
        BaseMcpConfig(server_id="")
    with pytest.raises(ValueError, match="'enabled' for server 's1' must be a boolean"):
        BaseMcpConfig(server_id="s1", enabled="true") # type: ignore
    with pytest.raises(ValueError, match="'tool_name_prefix' for server 's1' must be a string"):
        BaseMcpConfig(server_id="s1", tool_name_prefix=123) # type: ignore

def test_stdio_mcp_server_config_validation():
    # Valid minimal
    config = StdioMcpServerConfig(server_id="s1", command="mycmd")
    assert config.command == "mycmd"
    
    with pytest.raises(ValueError, match="'command' must be a non-empty string"):
        StdioMcpServerConfig(server_id="s1", command=None)
    with pytest.raises(ValueError, match="'command' must be a non-empty string"):
        StdioMcpServerConfig(server_id="s1", command="  ")
    with pytest.raises(ValueError, match="'args' must be a list of strings"):
        StdioMcpServerConfig(server_id="s1", command="c", args=["a", 1]) # type: ignore
    with pytest.raises(ValueError, match="'env' must be a Dict"):
        StdioMcpServerConfig(server_id="s1", command="c", env={"k": 1}) # type: ignore
    with pytest.raises(ValueError, match="'cwd' must be a string if provided"):
        StdioMcpServerConfig(server_id="s1", command="c", cwd=123) # type: ignore

def test_sse_mcp_server_config_validation():
    config = SseMcpServerConfig(server_id="s1", url="http://example.com")
    assert config.url == "http://example.com"

    with pytest.raises(ValueError, match="'url' must be a non-empty string"):
        SseMcpServerConfig(server_id="s1", url=None)
    with pytest.raises(ValueError, match="'token' must be a string if provided"):
        SseMcpServerConfig(server_id="s1", url="u", token=123) # type: ignore
    with pytest.raises(ValueError, match="'headers' must be a Dict"):
        SseMcpServerConfig(server_id="s1", url="u", headers={"h": 1}) # type: ignore

def test_streamable_http_mcp_server_config_validation():
    config = StreamableHttpMcpServerConfig(server_id="s1", url="http://example.com")
    assert config.url == "http://example.com"

    with pytest.raises(ValueError, match="'url' must be a non-empty string"):
        StreamableHttpMcpServerConfig(server_id="s1", url=None)
    with pytest.raises(ValueError, match="'token' must be a string if provided"):
        StreamableHttpMcpServerConfig(server_id="s1", url="u", token=123) # type: ignore
    with pytest.raises(ValueError, match="'headers' must be a Dict"):
        StreamableHttpMcpServerConfig(server_id="s1", url="u", headers={"h":1}) # type: ignore
