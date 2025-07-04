# file: autobyteus/tests/integration_tests/tools/mcp/test_mcp_registrar_integration.py
import json
import pytest
import os
from unittest.mock import MagicMock

# Refactored imports - McpSchemaMapper is no longer directly used here.
from autobyteus.tools.mcp import (
    McpConfigService,
    McpToolRegistrar,
    GenericMcpTool
)
from autobyteus.tools.mcp.types import StdioMcpServerConfig
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext

_MCP_SCRIPT_PATH_ENV_VAR_NAME = "TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH"

@pytest.fixture
def google_slides_mcp_script_path():
    """Provides the path to the google-slides-mcp script, skipping if not found."""
    script_path = os.environ.get(_MCP_SCRIPT_PATH_ENV_VAR_NAME)
    if not script_path or not os.path.exists(script_path):
        pytest.skip(f"Env var '{_MCP_SCRIPT_PATH_ENV_VAR_NAME}' not set or path invalid. Skipping MCP integration tests.")
    return script_path

expected_tools_details = [
    {"name": "create_presentation", "description": "Create a new Google Slides presentation", "params": [{"name": "title", "type": ParameterType.STRING, "required": True}]},
    {"name": "get_presentation", "description": "Get details about a Google Slides presentation", "params": [{"name": "presentationId", "type": ParameterType.STRING, "required": True}, {"name": "fields", "type": ParameterType.STRING, "required": False}]},
    {"name": "batch_update_presentation", "description": "Apply a batch of updates to a Google Slides presentation", "params": [{"name": "presentationId", "type": ParameterType.STRING, "required": True}, {"name": "requests", "type": ParameterType.ARRAY, "required": True, "array_item_schema": {"type": "object"}}, {"name": "writeControl", "type": ParameterType.OBJECT, "required": False}]},
    {"name": "get_page", "description": "Get details about a specific page (slide) in a presentation", "params": [{"name": "presentationId", "type": ParameterType.STRING, "required": True}, {"name": "pageObjectId", "type": ParameterType.STRING, "required": True}]},
    {"name": "summarize_presentation", "description": "Extract text content from all slides in a presentation for summarization purposes", "params": [{"name": "presentationId", "type": ParameterType.STRING, "required": True}, {"name": "include_notes", "type": ParameterType.BOOLEAN, "required": False}]}
]

@pytest.fixture
def mcp_test_environment(google_slides_mcp_script_path):
    """A fixture to set up and tear down the MCP test environment."""
    # Clean up singletons and registries before the test
    if McpConfigService in McpConfigService._instances:
        del McpConfigService._instances[McpConfigService]
    if McpToolRegistrar in McpToolRegistrar._instances:
        del McpToolRegistrar._instances[McpToolRegistrar]
    
    original_registry_definitions = default_tool_registry.get_all_definitions().copy()
    default_tool_registry._definitions.clear()

    # The config service is now managed by the registrar for targeted discovery
    config_service = McpConfigService()
    
    # The registrar is now a self-contained singleton.
    registrar = McpToolRegistrar()

    yield registrar, config_service  # Provide registrar and config service to the test

    # Teardown: Restore the original tool registry definitions.
    default_tool_registry._definitions = original_registry_definitions

@pytest.mark.asyncio
async def test_mcp_registrar_discovers_and_registers_google_slides_tools(mcp_test_environment, google_slides_mcp_script_path):
    """Tests that the registrar correctly discovers and registers tools."""
    registrar, config_service = mcp_test_environment
    
    # Define the config object but do not load it into the service manually
    gslides_config_dict = {
        "google-slides-mcp": {
            "transport_type": "stdio",
            "stdio_params": {
                "command": "node",
                "args": [google_slides_mcp_script_path],
                "env": {
                    "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID", ""),
                    "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
                    "GOOGLE_REFRESH_TOKEN": os.environ.get("GOOGLE_REFRESH_TOKEN", "")
                }
            },
            "enabled": True,
            "tool_name_prefix": "gslides",
        }
    }

    # Let the registrar handle adding the config and discovering
    await registrar.discover_and_register_tools(mcp_config=gslides_config_dict)
    
    # Verify the config was added to the service by the registrar
    assert config_service.get_config("google-slides-mcp") is not None

    # Test the registrar's internal cache
    assert registrar.is_server_registered("google-slides-mcp") is True
    tools_from_server = registrar.get_registered_tools_for_server("google-slides-mcp")
    assert len(tools_from_server) == len(expected_tools_details)
    
    all_mcp_tools = registrar.get_all_registered_mcp_tools()
    assert len(all_mcp_tools) == len(expected_tools_details)

    # Verify the main tool registry
    for expected_tool in expected_tools_details:
        registered_name = f"gslides_{expected_tool['name']}"
        tool_def = default_tool_registry.get_tool_definition(registered_name)
        assert tool_def is not None, f"Tool '{registered_name}' not found in registry."
        assert tool_def.name == registered_name
        assert tool_def.description == expected_tool["description"]
        assert callable(tool_def.custom_factory)
        
        assert tool_def.argument_schema is not None
        for expected_param_info in expected_tool["params"]:
            param_def = tool_def.argument_schema.get_parameter(expected_param_info["name"])
            assert param_def is not None
            assert param_def.param_type == expected_param_info["type"]
            assert param_def.required == expected_param_info["required"]
            
            # Add a more specific check for array item schemas
            if "array_item_schema" in expected_param_info:
                assert param_def.array_item_schema == expected_param_info["array_item_schema"]

@pytest.mark.asyncio
async def test_mcp_registrar_unregisters_tools_correctly(mcp_test_environment, google_slides_mcp_script_path):
    """Tests the full register-unregister-verify cycle."""
    registrar, _ = mcp_test_environment
    server_id = "gslides-test-unregister"

    gslides_config_dict = {
        server_id: {
            "transport_type": "stdio",
            "stdio_params": {"command": "node", "args": [google_slides_mcp_script_path]},
            "enabled": True,
            "tool_name_prefix": "temp_gslides",
        }
    }
    
    # 1. Register tools
    await registrar.discover_and_register_tools(mcp_config=gslides_config_dict)
    
    # 2. Verify registration
    assert registrar.is_server_registered(server_id)
    assert len(default_tool_registry.list_tools()) == len(expected_tools_details)
    assert default_tool_registry.get_tool_definition("temp_gslides_create_presentation") is not None
    
    # 3. Unregister tools
    unregistered = registrar.unregister_tools_from_server(server_id)
    assert unregistered is True
    
    # 4. Verify unregistration
    assert not registrar.is_server_registered(server_id)
    assert len(registrar.get_all_registered_mcp_tools()) == 0
    assert len(default_tool_registry.list_tools()) == 0
    assert default_tool_registry.get_tool_definition("temp_gslides_create_presentation") is None

@pytest.mark.asyncio
async def test_mcp_tool_execution_after_registration(mcp_test_environment, google_slides_mcp_script_path):
    """Tests the full flow: register, create from registry, and execute a tool."""
    registrar, _ = mcp_test_environment
    
    gslides_config_dict = {
        "google-slides-mcp": {
            "transport_type": "stdio",
            "stdio_params": {
                "command": "node",
                "args": [google_slides_mcp_script_path],
                "env": {
                    "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID", ""),
                    "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
                    "GOOGLE_REFRESH_TOKEN": os.environ.get("GOOGLE_REFRESH_TOKEN", "")
                }
            },
            "tool_name_prefix": "gslides",
        }
    }
    
    await registrar.discover_and_register_tools(mcp_config=gslides_config_dict)
    
    tool_name = "create_presentation" 
    registered_tool_name = f"gslides_{tool_name}"
    create_tool = default_tool_registry.create_tool(registered_tool_name)
    assert isinstance(create_tool, GenericMcpTool)
    
    mock_context = MagicMock(spec=AgentContext)
    mock_context.agent_id = "integration_test_agent"
    test_title = f"Test Presentation {os.urandom(4).hex()}"
    
    result = await create_tool.execute(context=mock_context, title=test_title)
    
    assert isinstance(result, str)
    
    response_data = json.loads(result)
    assert response_data.get("title") == test_title
    assert "presentationId" in response_data

@pytest.mark.asyncio
async def test_mcp_registrar_list_remote_tools_previews_without_side_effects(mcp_test_environment, google_slides_mcp_script_path):
    """
    Tests that `list_remote_tools` previews correctly without altering global state.
    """
    registrar, config_service = mcp_test_environment

    gslides_config_dict = {
        "google-slides-mcp-preview": { # Use a different server_id for clarity
            "transport_type": "stdio",
            "stdio_params": {
                "command": "node",
                "args": [google_slides_mcp_script_path],
                "env": {
                    "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID", ""),
                    "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
                    "GOOGLE_REFRESH_TOKEN": os.environ.get("GOOGLE_REFRESH_TOKEN", "")
                }
            },
            "tool_name_prefix": "gslides_preview", # Use a different prefix
        }
    }

    # Call the preview method
    tool_definitions = await registrar.list_remote_tools(mcp_config=gslides_config_dict)
    
    # 1. Assert that the returned definitions are correct
    assert len(tool_definitions) == len(expected_tools_details)
    for expected_tool in expected_tools_details:
        previewed_name = f"gslides_preview_{expected_tool['name']}"
        # Find the corresponding definition in the returned list
        tool_def = next((td for td in tool_definitions if td.name == previewed_name), None)
        
        assert tool_def is not None, f"Tool '{previewed_name}' not found in preview list."
        assert tool_def.description == expected_tool["description"]
        assert callable(tool_def.custom_factory) # Check that it's a usable definition
        
        assert tool_def.argument_schema is not None
        for expected_param_info in expected_tool["params"]:
            param_def = tool_def.argument_schema.get_parameter(expected_param_info["name"])
            assert param_def is not None
            assert param_def.param_type == expected_param_info["type"]
            assert param_def.required == expected_param_info["required"]
    
    # 2. Assert that there are no side effects
    assert config_service.get_config("google-slides-mcp-preview") is None
    assert len(config_service.get_all_configs()) == 0
    
    assert default_tool_registry.get_tool_definition("gslides_preview_create_presentation") is None
    assert len(default_tool_registry.list_tools()) == 0
