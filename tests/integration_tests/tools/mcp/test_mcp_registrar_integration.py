import pytest
import asyncio
import os
from unittest.mock import MagicMock

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
from autobyteus.agent.context import AgentContext

# Environment variable name for the MCP server script path
_MCP_SCRIPT_PATH_ENV_VAR_NAME = "TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH"

@pytest.fixture
def google_slides_mcp_script_path():
    """
    Fixture to provide the path to the google-slides-mcp script from an environment variable.
    Skips the test if the environment variable is not set or the path is invalid.
    """
    script_path = os.environ.get(_MCP_SCRIPT_PATH_ENV_VAR_NAME)
    
    if not script_path:
        pytest.skip(
            f"Environment variable '{_MCP_SCRIPT_PATH_ENV_VAR_NAME}' is not set. "
            "This variable must point to the google-slides-mcp executable script for this integration test."
        )
    
    if not os.path.exists(script_path):
        pytest.skip(
            f"MCP server script specified by '{_MCP_SCRIPT_PATH_ENV_VAR_NAME}' "
            f"({script_path}) not found. Skipping integration test."
        )
        
    return script_path

# This can remain at the module level as it doesn't depend on the script path
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

# Helper to set up the environment for tests
@pytest.fixture
def mcp_test_environment(google_slides_mcp_script_path):
    """A fixture to set up and tear down the MCP test environment."""
    # Ensure singletons are clean before the test
    if McpConfigService in McpConfigService._instances:
        del McpConfigService._instances[McpConfigService]
    if McpConnectionManager in McpConnectionManager._instances:
        del McpConnectionManager._instances[McpConnectionManager]
    
    original_registry_definitions = default_tool_registry._definitions.copy()
    default_tool_registry._definitions.clear()

    # Configuration for the test
    config_dict = {
        "google-slides-mcp": {
            "transport_type": "stdio",
            "command": "node",
            "args": [google_slides_mcp_script_path],
            "enabled": True,
            "tool_name_prefix": "gslides", # Use a prefix for testing
            "env": {
                "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID", ""),
                "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
                "GOOGLE_REFRESH_TOKEN": os.environ.get("GOOGLE_REFRESH_TOKEN", "")
            }
        }
    }

    config_service = McpConfigService()
    config_service.load_configs(config_dict)
    conn_manager = McpConnectionManager(config_service=config_service)
    schema_mapper = McpSchemaMapper()
    registrar = McpToolRegistrar(
        config_service=config_service,
        conn_manager=conn_manager,
        schema_mapper=schema_mapper,
        tool_registry=default_tool_registry
    )

    yield registrar, conn_manager # Provide the components to the test

    # Teardown
    # The `finally` block in the test functions will call conn_manager.cleanup()
    default_tool_registry._definitions = original_registry_definitions


@pytest.mark.asyncio
async def test_mcp_registrar_discovers_and_registers_google_slides_tools(mcp_test_environment):
    """Tests that the registrar correctly discovers and registers tools."""
    registrar, conn_manager = mcp_test_environment
    
    try:
        await registrar.discover_and_register_tools()

        registered_tool_count = len(default_tool_registry.list_tool_names())
        assert registered_tool_count == len(expected_tools_details), \
            f"Expected {len(expected_tools_details)} tools to be registered, but found {registered_tool_count}."

        for expected_tool in expected_tools_details:
            registered_name = f"gslides_{expected_tool['name']}" # Check for prefix
            tool_def = default_tool_registry.get_tool_definition(registered_name)

            assert tool_def is not None, f"Tool '{registered_name}' not found in registry."
            assert tool_def.name == registered_name
            assert tool_def.description == expected_tool["description"]
            assert tool_def.tool_class is None
            assert callable(tool_def.custom_factory)
            
            assert isinstance(tool_def.argument_schema, ParameterSchema)
            for expected_param_info in expected_tool["params"]:
                param_def = tool_def.argument_schema.get_parameter(expected_param_info["name"])
                assert param_def is not None
                assert param_def.param_type == expected_param_info["type"]
                assert param_def.required == expected_param_info["required"]
    finally:
        await conn_manager.cleanup()


@pytest.mark.asyncio
async def test_mcp_tool_execution_after_registration(mcp_test_environment):
    """Tests the full flow: register, create from registry, and execute a tool."""
    registrar, conn_manager = mcp_test_environment
    
    try:
        # 1. Register tools
        await registrar.discover_and_register_tools()
        
        # 2. Create tool from registry
        tool_name = "gslides_create_presentation"
        create_tool = default_tool_registry.create_tool(tool_name)
        
        assert isinstance(create_tool, GenericMcpTool)
        
        # 3. Execute the tool
        mock_context = MagicMock(spec=AgentContext)
        mock_context.agent_id = "integration_test_agent"
        test_title = f"Test Presentation {os.urandom(4).hex()}"
        
        result = await create_tool.execute(context=mock_context, title=test_title)
        
        # 4. Assert the result
        assert result is not None
        # The result from GenericMcpTool._execute is the mcp.types.ToolResult object
        assert hasattr(result, 'content') and result.content
        assert isinstance(result.content[0].text, str)
        
        # Check that the returned JSON string contains our title
        response_data = json.loads(result.content[0].text)
        assert response_data.get("title") == test_title
        assert "presentationId" in response_data

    finally:
        await conn_manager.cleanup()
