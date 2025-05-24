# file: autobyteus/tests/unit_tests/mcp/test_config_service.py
import pytest
import json
import os
from typing import List, Dict, Any

# Updated import path
from autobyteus.tools.mcp import (
    McpConfigService,
    McpConfig,
    StdioServerParametersConfig,
    SseTransportConfig,
    McpTransportType,
    StreamableHttpConfig 
)

# Test Data (adapted from user examples to fit dataclass structure)
# UPDATED: 'id' field changed to 'server_name' in all test data dictionaries

USER_EXAMPLE_1_FLAT_DICT = {
    "google-slides-mcp": { # This key is the server_name
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
        # 'server_name' will be injected from the key 'google-slides-mcp' by _process_config_dict
    }
}

USER_EXAMPLE_2_FLAT_DICT = {
    "google-maps": { # This key is the server_name
        "transport_type": "stdio",
        "enabled": True,
        "stdio_params": {
            "command": "docker",
            "args": ["run", "-i", "--rm", "-e", "GOOGLE_MAPS_API_KEY", "mcp/google-maps"],
            "env": {"GOOGLE_MAPS_API_KEY": "<YOUR_API_KEY>"}
        }
    }
}

# MODIFIED: USER_EXAMPLE_3_FLAT_DICT to be more concrete
USER_EXAMPLE_3_FLAT_DICT = {
    "live-collab-mcp": { # This key is the server_name
        "transport_type": "sse",
        "enabled": True,
        "sse_params": {
            "url": "https://live-collab.example.com/api/v1/events" # More specific URL
        }
    }
}

USER_EXAMPLE_4_FLAT_DICT = {
    "mcp-deepwiki": { # This key is the server_name
        "transport_type": "stdio",
        "stdio_params": {
            "command": "npx",
            "args": ["-y", "mcp-deepwiki@latest"]
        }
    }
}

VALID_STDIO_CONFIG_LIST_ITEM = {
    "server_name": "stdio_server_1", 
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
    "server_name": "sse_server_1", 
    "transport_type": "sse",
    "enabled": False,
    "tool_name_prefix": "sse_remote_",
    "sse_params": {
        "url": "http://localhost:8000/events",
        "token": "secret-token",
        "headers": {"X-Custom-Header": "value"}
    }
}

TEST_ADD_STDIO_CONFIG_DICT = {
    "server_name": "google-doc-mcp", 
    "transport_type": "stdio",
    "enabled": True,
    "tool_name_prefix": "gdoc_",
    "stdio_params": {
        "command": "node",
        "args": ["/path/to/google-doc-mcp/index.js"],
        "env": {"API_KEY": "doc_api_key"}
    }
}

TEST_ADD_SSE_CONFIG_DICT = {
    "server_name": "google-calendar-mcp", 
    "transport_type": "sse",
    "enabled": True,
    "sse_params": {
        "url": "https://calendar-mcp.example.com/api/events",
        "token": "cal_token_123",
        "headers": {"X-App-ID": "calendar_app"}
    }
}


@pytest.fixture
def mcp_config_service() -> McpConfigService:
    service = McpConfigService()
    service.clear_configs() 
    return service

def test_load_configs_from_list_valid_stdio(mcp_config_service: McpConfigService):
    configs_data = [VALID_STDIO_CONFIG_LIST_ITEM]
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 1
    assert len(mcp_config_service.get_all_configs()) == 1
    
    config = mcp_config_service.get_config("stdio_server_1")
    assert config is not None
    assert config.server_name == "stdio_server_1" 
    assert config.transport_type == McpTransportType.STDIO
    assert config.enabled is True
    assert config.tool_name_prefix == "std_"
    assert isinstance(config.stdio_params, StdioServerParametersConfig)
    assert config.stdio_params.command == "python"
    assert config.stdio_params.args == ["-m", "my_mcp_server"]
    assert config.stdio_params.env == {"PYTHONUNBUFFERED": "1"}
    assert config.stdio_params.cwd == "/tmp"
    assert config.sse_params is None

def test_load_configs_from_list_valid_sse(mcp_config_service: McpConfigService):
    configs_data = [VALID_SSE_CONFIG_LIST_ITEM]
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 1
    assert len(mcp_config_service.get_all_configs()) == 1

    config = mcp_config_service.get_config("sse_server_1")
    assert config is not None
    assert config.server_name == "sse_server_1" 
    assert config.transport_type == McpTransportType.SSE
    assert config.enabled is False
    assert config.tool_name_prefix == "sse_remote_"
    assert isinstance(config.sse_params, SseTransportConfig)
    assert config.sse_params.url == "http://localhost:8000/events"
    assert config.sse_params.token == "secret-token"
    assert config.sse_params.headers == {"X-Custom-Header": "value"}
    assert config.stdio_params is None

def test_load_configs_from_list_mixed(mcp_config_service: McpConfigService):
    configs_data = [VALID_STDIO_CONFIG_LIST_ITEM, VALID_SSE_CONFIG_LIST_ITEM]
    loaded = mcp_config_service.load_configs(configs_data)
    assert len(loaded) == 2
    assert len(mcp_config_service.get_all_configs()) == 2
    assert mcp_config_service.get_config("stdio_server_1") is not None
    assert mcp_config_service.get_config("sse_server_1") is not None

def test_load_configs_from_file_list_format(mcp_config_service: McpConfigService, tmp_path):
    file_content = [VALID_STDIO_CONFIG_LIST_ITEM, VALID_SSE_CONFIG_LIST_ITEM]
    config_file = tmp_path / "mcp_config_list.json"
    config_file.write_text(json.dumps(file_content))

    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 2
    assert len(mcp_config_service.get_all_configs()) == 2
    assert mcp_config_service.get_config("stdio_server_1") is not None
    assert mcp_config_service.get_config("sse_server_1") is not None

def test_load_configs_from_file_dict_format_user_example1(mcp_config_service: McpConfigService, tmp_path):
    config_file = tmp_path / "mcp_config_ex1.json"
    config_file.write_text(json.dumps(USER_EXAMPLE_1_FLAT_DICT))
    
    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 1
    config = mcp_config_service.get_config("google-slides-mcp")
    assert config is not None
    assert config.server_name == "google-slides-mcp" 
    assert config.transport_type == McpTransportType.STDIO
    assert config.stdio_params.command == "node"

def test_load_configs_from_file_dict_format_user_example2(mcp_config_service: McpConfigService, tmp_path):
    config_file = tmp_path / "mcp_config_ex2.json"
    config_file.write_text(json.dumps(USER_EXAMPLE_2_FLAT_DICT))

    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 1
    config = mcp_config_service.get_config("google-maps")
    assert config is not None
    assert config.server_name == "google-maps" 
    assert config.transport_type == McpTransportType.STDIO
    assert config.stdio_params.command == "docker"
    assert "mcp/google-maps" in config.stdio_params.args

# MODIFIED: Test name and assertions for USER_EXAMPLE_3
def test_load_configs_from_file_dict_format_user_example3_sse(mcp_config_service: McpConfigService, tmp_path):
    config_file = tmp_path / "mcp_config_ex3.json"
    config_file.write_text(json.dumps(USER_EXAMPLE_3_FLAT_DICT))

    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 1
    config = mcp_config_service.get_config("live-collab-mcp") # MODIFIED server name
    assert config is not None
    assert config.server_name == "live-collab-mcp" # MODIFIED server name
    assert config.transport_type == McpTransportType.SSE
    assert config.sse_params.url == "https://live-collab.example.com/api/v1/events" # MODIFIED URL

def test_load_configs_from_file_dict_format_user_example4_defaults(mcp_config_service: McpConfigService, tmp_path):
    config_file = tmp_path / "mcp_config_ex4.json"
    config_file.write_text(json.dumps(USER_EXAMPLE_4_FLAT_DICT))

    loaded = mcp_config_service.load_configs(str(config_file))
    assert len(loaded) == 1
    config = mcp_config_service.get_config("mcp-deepwiki")
    assert config is not None
    assert config.server_name == "mcp-deepwiki" 
    assert config.transport_type == McpTransportType.STDIO
    assert config.stdio_params.command == "npx"
    assert config.enabled is True 
    assert config.stdio_params.env == {} 

@pytest.mark.parametrize("invalid_data, error_message_match", [
    ([{"transport_type": "stdio"}], "missing 'server_name' field"), 
    ({"myid": {"transport_type": "invalid_type"}}, "is not a valid McpTransportType"), 
    ({"myid": {"transport_type": "stdio"}}, "requires 'stdio_params'"), 
    ({"myid": {"transport_type": "sse"}}, "requires 'sse_params'"), 
    ({"myid": {"transport_type": "stdio", "stdio_params": {"args": ["hi"]}}}, "command' must be a non-empty string"), 
    ({"myid": {"transport_type": "sse", "sse_params": {}}}, "'url' must be a non-empty string"), 
    ([{"server_name": "x", "transport_type": "stdio", "stdio_params": {"command": 123}}], "command' must be a non-empty string"), 
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

def test_add_config_with_mcp_object_stdio(mcp_config_service: McpConfigService):
    mcp_object = McpConfig(**TEST_ADD_STDIO_CONFIG_DICT)
    
    returned_config = mcp_config_service.add_config(mcp_object)
    assert returned_config == mcp_object
    
    assert len(mcp_config_service.get_all_configs()) == 1
    stored_config = mcp_config_service.get_config("google-doc-mcp")
    assert stored_config is not None
    assert stored_config.server_name == "google-doc-mcp" 
    assert stored_config.transport_type == McpTransportType.STDIO
    assert stored_config.enabled is True
    assert stored_config.tool_name_prefix == "gdoc_"
    assert isinstance(stored_config.stdio_params, StdioServerParametersConfig)
    assert stored_config.stdio_params.command == "node"
    assert stored_config.stdio_params.args == ["/path/to/google-doc-mcp/index.js"]
    assert stored_config.stdio_params.env == {"API_KEY": "doc_api_key"}

def test_add_config_with_dict_sse(mcp_config_service: McpConfigService):
    config_dict = TEST_ADD_SSE_CONFIG_DICT.copy()
    
    returned_config = mcp_config_service.add_config(config_dict)
    
    assert len(mcp_config_service.get_all_configs()) == 1
    stored_config = mcp_config_service.get_config("google-calendar-mcp")
    
    assert stored_config is not None
    assert stored_config == returned_config
    assert stored_config.server_name == "google-calendar-mcp" 
    assert stored_config.transport_type == McpTransportType.SSE
    assert stored_config.enabled is True
    assert isinstance(stored_config.sse_params, SseTransportConfig)
    assert stored_config.sse_params.url == "https://calendar-mcp.example.com/api/events"
    assert stored_config.sse_params.token == "cal_token_123"
    assert stored_config.sse_params.headers == {"X-App-ID": "calendar_app"}

def test_add_config_overwrites_existing(mcp_config_service: McpConfigService, caplog):
    config_v1_dict = {
        "server_name": "common_server", 
        "transport_type": "stdio",
        "stdio_params": {"command": "cmd_v1"}
    }
    config_v2_obj = McpConfig(
        server_name="common_server", 
        transport_type="stdio",
        enabled=False,
        stdio_params=StdioServerParametersConfig(command="cmd_v2", args=["arg1"])
    )

    mcp_config_service.add_config(config_v1_dict)
    stored_v1 = mcp_config_service.get_config("common_server")
    assert stored_v1 is not None
    assert stored_v1.stdio_params.command == "cmd_v1"
    assert stored_v1.enabled is True 

    caplog.clear()
    mcp_config_service.add_config(config_v2_obj)
    assert "Overwriting existing MCP config with server_name 'common_server'" in caplog.text 

    assert len(mcp_config_service.get_all_configs()) == 1
    stored_v2 = mcp_config_service.get_config("common_server")
    assert stored_v2 is not None
    assert stored_v2.stdio_params.command == "cmd_v2"
    assert stored_v2.stdio_params.args == ["arg1"]
    assert stored_v2.enabled is False

def test_add_config_with_invalid_dict_missing_id(mcp_config_service: McpConfigService): 
    invalid_dict = {"transport_type": "stdio", "stdio_params": {"command": "cmd"}}
    with pytest.raises(ValueError, match="Configuration dictionary must contain a 'server_name' field."): 
        mcp_config_service.add_config(invalid_dict)

@pytest.mark.parametrize("invalid_field_data, error_message_match", [
    ({"server_name": "test", "transport_type": "invalid_one"}, "is not a valid McpTransportType"), 
    ({"server_name": "test", "transport_type": "stdio"}, "requires 'stdio_params'"), 
    ({"server_name": "test", "transport_type": "stdio", "stdio_params": {"command": None}}, "command' must be a non-empty string"), 
])
def test_add_config_with_invalid_dict_bad_data(mcp_config_service: McpConfigService, invalid_field_data, error_message_match):
    with pytest.raises(ValueError, match=error_message_match):
        mcp_config_service.add_config(invalid_field_data)

def test_add_config_with_unsupported_type(mcp_config_service: McpConfigService):
    with pytest.raises(TypeError, match="Unsupported input type for add_config"):
        mcp_config_service.add_config(12345) # type: ignore
    with pytest.raises(TypeError, match="Unsupported input type for add_config"):
        mcp_config_service.add_config([TEST_ADD_STDIO_CONFIG_DICT]) # type: ignore

def test_get_config_non_existent(mcp_config_service: McpConfigService):
    assert mcp_config_service.get_config("non_existent_server_name") is None 

def test_get_all_configs_empty(mcp_config_service: McpConfigService):
    assert mcp_config_service.get_all_configs() == []

def test_load_configs_duplicate_id_overwrites(mcp_config_service: McpConfigService, caplog): 
    configs1 = [{"server_name": "server1", "transport_type": "stdio", "stdio_params": {"command": "cmd1"}}] 
    configs2 = [{"server_name": "server1", "transport_type": "stdio", "stdio_params": {"command": "cmd2"}}] 
    
    mcp_config_service.load_configs(configs1)
    assert mcp_config_service.get_config("server1").stdio_params.command == "cmd1"
    
    mcp_config_service.load_configs(configs2) 
    assert len(mcp_config_service.get_all_configs()) == 1
    assert mcp_config_service.get_config("server1").stdio_params.command == "cmd2"
    assert "Duplicate MCP config server_name 'server1' found" in caplog.text 

def test_clear_configs(mcp_config_service: McpConfigService):
    mcp_config_service.load_configs([VALID_STDIO_CONFIG_LIST_ITEM])
    assert len(mcp_config_service.get_all_configs()) == 1
    mcp_config_service.clear_configs()
    assert len(mcp_config_service.get_all_configs()) == 0
    assert mcp_config_service.get_config(VALID_STDIO_CONFIG_LIST_ITEM["server_name"]) is None 

def test_nested_dataclass_construction_from_dict():
    raw_data = {
        "server_name": "test_server", 
        "transport_type": "stdio",
        "stdio_params": { 
            "command": "my_cmd",
            "args": ["arg1"],
            "env": {"K": "V"},
            "cwd": "/data"
        }
    }
    config = McpConfig(**raw_data)
    assert isinstance(config.stdio_params, StdioServerParametersConfig)
    assert config.stdio_params.command == "my_cmd"
    assert config.stdio_params.cwd == "/data"

    raw_data_sse = {
        "server_name": "test_sse_server", 
        "transport_type": "sse",
        "sse_params": { 
            "url": "http://test.com",
            "token": "tok"
        }
    }
    config_sse = McpConfig(**raw_data_sse)
    assert isinstance(config_sse.sse_params, SseTransportConfig)
    assert config_sse.sse_params.url == "http://test.com"
    assert config_sse.sse_params.token == "tok"

def test_mcpconfig_post_init_type_coercion_and_validation():
    cfg = McpConfig(server_name="s1", transport_type="stdio", stdio_params={"command": "c"}) 
    assert cfg.transport_type == McpTransportType.STDIO

    with pytest.raises(ValueError, match="'server_name' must be a non-empty string"): 
        McpConfig(server_name="", transport_type="stdio", stdio_params={"command": "c"}) 

    with pytest.raises(ValueError, match="is not a valid McpTransportType"):
        McpConfig(server_name="s1", transport_type="invalid", stdio_params={"command": "c"}) 

    with pytest.raises(TypeError, match="must be a McpTransportType enum or a valid string"):
        McpConfig(server_name="s1", transport_type=123, stdio_params={"command": "c"}) # type: ignore 

    with pytest.raises(TypeError, match="'stdio_params' must be an instance of StdioServerParametersConfig or a compatible dict"):
        McpConfig(server_name="s1", transport_type="stdio", stdio_params="not_a_dict") # type: ignore 
        
    with pytest.raises(TypeError, match="'sse_params' must be an instance of SseTransportConfig or a compatible dict"):
        McpConfig(server_name="s1", transport_type="sse", sse_params="not_a_dict") # type: ignore 
        
def test_stdio_config_post_init_validations():
    with pytest.raises(ValueError, match="'command' must be a non-empty string"):
        StdioServerParametersConfig(command="")
    with pytest.raises(ValueError, match="'args' must be a list of strings"):
        StdioServerParametersConfig(command="c", args="not_a_list") # type: ignore
    with pytest.raises(ValueError, match="'env' must be a Dict"):
        StdioServerParametersConfig(command="c", env=["not_a_dict"]) # type: ignore
    with pytest.raises(ValueError, match="'cwd' must be a string if provided"):
        StdioServerParametersConfig(command="c", cwd=123) # type: ignore

def test_sse_config_post_init_validations():
    with pytest.raises(ValueError, match="'url' must be a non-empty string"):
        SseTransportConfig(url="")
    with pytest.raises(ValueError, match="'token' must be a string if provided"):
        SseTransportConfig(url="u", token=123) # type: ignore
    with pytest.raises(ValueError, match="'headers' must be a Dict"):
        SseTransportConfig(url="u", headers=["not_a_dict"]) # type: ignore

def test_streamable_http_config_post_init_validations():
    from autobyteus.tools.mcp.types import StreamableHttpConfig 
    with pytest.raises(ValueError, match="'url' must be a non-empty string"):
        StreamableHttpConfig(url="")
    with pytest.raises(ValueError, match="'token' must be a string if provided"):
        StreamableHttpConfig(url="u", token=123) # type: ignore
    with pytest.raises(ValueError, match="'headers' must be a Dict"):
        StreamableHttpConfig(url="u", headers=["not_a_dict"]) # type: ignore

    with pytest.raises(ValueError, match="requires 'streamable_http_params'"):
        McpConfig(server_name="s_http", transport_type="streamable_http") 
    
    valid_http_params_dict = {"url": "http://example.com/stream"}
    cfg_http = McpConfig(server_name="s_http", transport_type="streamable_http", streamable_http_params=valid_http_params_dict) 
    assert isinstance(cfg_http.streamable_http_params, StreamableHttpConfig)
    assert cfg_http.streamable_http_params.url == "http://example.com/stream"

    with pytest.raises(TypeError, match="'streamable_http_params' must be an instance of StreamableHttpConfig or a compatible dict"):
        McpConfig(server_name="s1", transport_type="streamable_http", streamable_http_params="not_a_dict") # type: ignore 
