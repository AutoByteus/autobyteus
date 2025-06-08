import pytest
import asyncio
import os

from autobyteus.tools.mcp import (
    McpConfigService,
    McpConnectionManager,
    McpSchemaMapper,
    McpToolRegistrar,
    GenericMcpTool,
    StdioMcpServerConfig,
    McpTransportType
)
from autobyteus.tools.registry import default_tool_registry, ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

# Environment variable name for the MCP server script path
_MCP_SCRIPT_PATH_ENV_VAR_NAME = "TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH"
# Retrieve the script path from the environment variable
_google_slides_mcp_script_path_from_env = os.environ.get(_MCP_SCRIPT_PATH_ENV_VAR_NAME)

# Define skip conditions and reasons evaluated at test collection time
_SKIP_IF_ENV_VAR_NOT_SET = _google_slides_mcp_script_path_from_env is None
_REASON_ENV_VAR_NOT_SET = (
    f"Environment variable '{_MCP_SCRIPT_PATH_ENV_VAR_NAME}' is not set. "
    "This variable must point to the google-slides-mcp executable script for this integration test."
)

_SKIP_IF_PATH_INVALID = (
    not _SKIP_IF_ENV_VAR_NOT_SET and # Only check path if env var was set
    not os.path.exists(_google_slides_mcp_script_path_from_env)
)
_REASON_PATH_INVALID = (
    f"MCP server script specified by '{_MCP_SCRIPT_PATH_ENV_VAR_NAME}' "
    f"({_google_slides_mcp_script_path_from_env}) not found. Skipping integration test."
)


# Configuration for the google-slides-mcp server
# This dictionary is defined globally but will only be used if the test is not skipped.
# The _google_slides_mcp_script_path_from_env will be valid if the test runs.
google_slides_mcp_config_dict = {
    "google-slides-mcp": {
        "transport_type": "stdio",
        "command": "node",
        "args": [_google_slides_mcp_script_path_from_env], # Uses path from env var
        "enabled": True,
        "tool_name_prefix": None,
        "env": {
            "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID", "YOUR_TEST_CLIENT_ID_FROM_ENV"),
            "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_TEST_CLIENT_SECRET_FROM_ENV"),
            "GOOGLE_REFRESH_TOKEN": os.environ.get("GOOGLE_REFRESH_TOKEN", "YOUR_TEST_REFRESH_TOKEN_FROM_ENV")
        }
    }
} if not _SKIP_IF_ENV_VAR_NOT_SET else {} # Define dict only if env var is set, else empty

expected_tools_details = [
    {
        "name": "create_presentation",
        "description": "Create a new Google Slides presentation",
        "params": [{"name": "title", "type": ParameterType.STRING, "required": True}]
    },
    {
        "name": "get_presentation",
        "description": "Get details about a Google Slides presentation",
        "params": [
            {"name": "presentationId", "type": ParameterType.STRING, "required": True},
            {"name": "fields", "type": ParameterType.STRING, "required": False}
        ]
    },
    {
        "name": "batch_update_presentation",
        "description": "Apply a batch of updates to a Google Slides presentation",
        "params": [
            {"name": "presentationId", "type": ParameterType.STRING, "required": True},
            {"name": "requests", "type": ParameterType.ARRAY, "required": True, "item_schema_type": "object"},
            {"name": "writeControl", "type": ParameterType.OBJECT, "required": False}
        ]
    },
    {
        "name": "get_page",
        "description": "Get details about a specific page (slide) in a presentation",
        "params": [
            {"name": "presentationId", "type": ParameterType.STRING, "required": True},
            {"name": "pageObjectId", "type": ParameterType.STRING, "required": True}
        ]
    },
    {
        "name": "summarize_presentation",
        "description": "Extract text content from all slides in a presentation for summarization purposes",
        "params": [
            {"name": "presentationId", "type": ParameterType.STRING, "required": True},
            {"name": "include_notes", "type": ParameterType.BOOLEAN, "required": False}
        ]
    }
]

@pytest.mark.skipif(_SKIP_IF_ENV_VAR_NOT_SET, reason=_REASON_ENV_VAR_NOT_SET)
@pytest.mark.skipif(_SKIP_IF_PATH_INVALID, reason=_REASON_PATH_INVALID)
@pytest.mark.asyncio
async def test_mcp_registrar_discovers_and_registers_google_slides_tools():
    """
    Integration test for McpToolRegistrar with a real STDIO MCP server.
    Relies on TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH environment variable.
    """
    # Ensure singletons are in a clean state for this test
    if McpConfigService in McpConfigService._instances:
        del McpConfigService._instances[McpConfigService]
    if McpConnectionManager in McpConnectionManager._instances:
        del McpConnectionManager._instances[McpConnectionManager]
    
    original_registry_definitions = default_tool_registry._definitions.copy()
    default_tool_registry._definitions.clear()

    config_service = McpConfigService()
    # The google_slides_mcp_config_dict will be valid here because the test wouldn't run if env var was missing.
    loaded_configs = config_service.load_configs(google_slides_mcp_config_dict)
    assert len(loaded_configs) == 1
    assert isinstance(loaded_configs[0], StdioMcpServerConfig)
    assert loaded_configs[0].command == "node"
    # _google_slides_mcp_script_path_from_env is guaranteed to be non-None here by skipif
    assert loaded_configs[0].args == [_google_slides_mcp_script_path_from_env]
    assert loaded_configs[0].env["GOOGLE_CLIENT_ID"] == os.environ.get("GOOGLE_CLIENT_ID", "YOUR_TEST_CLIENT_ID_FROM_ENV")

    conn_manager = McpConnectionManager(config_service=config_service)
    schema_mapper = McpSchemaMapper()
    
    registrar = McpToolRegistrar(
        config_service=config_service,
        conn_manager=conn_manager,
        schema_mapper=schema_mapper,
        tool_registry=default_tool_registry
    )

    registered_tool_count_before = len(default_tool_registry.list_tool_names())

    try:
        await registrar.discover_and_register_tools()

        registered_tool_count_after = len(default_tool_registry.list_tool_names())
        assert registered_tool_count_after == registered_tool_count_before + len(expected_tools_details), \
            f"Expected {len(expected_tools_details)} tools to be registered."

        for expected_tool in expected_tools_details:
            tool_name = expected_tool["name"]
            registered_name = tool_name # No prefix in this config

            tool_def = default_tool_registry.get_tool_definition(registered_name)

            assert tool_def is not None, f"Tool '{registered_name}' not found in registry."
            assert tool_def.name == registered_name
            assert tool_def.description == expected_tool["description"]
            assert tool_def.tool_class == GenericMcpTool
            assert callable(tool_def.custom_factory), f"Custom factory for '{registered_name}' is not callable."
            
            assert isinstance(tool_def.argument_schema, ParameterSchema), \
                f"Argument schema for '{registered_name}' is not a ParameterSchema instance."

            for expected_param_info in expected_tool["params"]:
                param_def = tool_def.argument_schema.get_parameter(expected_param_info["name"])
                assert param_def is not None, \
                    f"Parameter '{expected_param_info['name']}' not found in schema for tool '{registered_name}'."
                assert param_def.param_type == expected_param_info["type"], \
                    f"Parameter '{param_def.name}' type mismatch for tool '{registered_name}'. Expected {expected_param_info['type']}, got {param_def.param_type}."
                assert param_def.required == expected_param_info["required"], \
                    f"Parameter '{param_def.name}' required mismatch for tool '{registered_name}'."
                
                if expected_param_info["type"] == ParameterType.ARRAY:
                    assert param_def.array_item_schema is not None, \
                        f"Parameter '{param_def.name}' (array) missing item schema for tool '{registered_name}'."
                    if "item_schema_type" in expected_param_info:
                        item_schema = param_def.array_item_schema
                        if isinstance(item_schema, dict):
                             assert item_schema.get("type") == expected_param_info["item_schema_type"], \
                                f"Array item type mismatch for '{param_def.name}' in tool '{registered_name}'."
                        elif item_schema is True and expected_param_info["item_schema_type"] == "any":
                            pass 
                        else:
                            pytest.fail(f"Unexpected array_item_schema format or type for '{param_def.name}' in tool '{registered_name}'.")
    finally:
        await conn_manager.cleanup()
        default_tool_registry._definitions = original_registry_definitions
        if McpConfigService in McpConfigService._instances:
            del McpConfigService._instances[McpConfigService]
        if McpConnectionManager in McpConnectionManager._instances:
            del McpConnectionManager._instances[McpConnectionManager]

