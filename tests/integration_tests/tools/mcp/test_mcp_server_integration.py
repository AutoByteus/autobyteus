# file: autobyteus/tests/integration_tests/tools/mcp/test_mcp_server_integration.py
import pytest
import shutil
import logging
from mcp import types as mcp_types

from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.server import StdioManagedMcpServer
from autobyteus.tools.mcp.types import StdioMcpServerConfig

logger = logging.getLogger(__name__)

@pytest.fixture
def npx_is_available():
    """Skips tests if npx is not found in the system's PATH."""
    if not shutil.which("npx"):
        pytest.skip("`npx` command not found. Skipping browsermcp integration test.")

@pytest.mark.asyncio
async def test_stdio_managed_server_lists_browsermcp_tools(npx_is_available):
    """
    Tests that a StdioManagedMcpServer can be instantiated and can successfully
    discover tools from a real-world MCP server (@browsermcp/mcp).
    """
    # 1. Define the real-world MCP server configuration
    browsermcp_config_dict = {
        "browsermcp": {
            "transport_type": "stdio",
            "enabled": True,
            "stdio_params": {
                "command": "npx",
                "args": ["--yes", "@browsermcp/mcp@latest"] # --yes prevents interactive prompts
            }
        }
    }

    # 2. Use McpConfigService to parse the configuration
    config_service = McpConfigService()
    # Clear any configs from other tests
    config_service.clear_configs()
    
    config_object = config_service.load_config_from_dict(browsermcp_config_dict)
    
    assert isinstance(config_object, StdioMcpServerConfig)
    assert config_object.server_id == "browsermcp"

    # 3. Instantiate the StdioManagedMcpServer
    server = StdioManagedMcpServer(config_object)
    
    try:
        # 4. Call list_remote_tools, which handles connection implicitly
        remote_tools = await server.list_remote_tools()

        # 5. Assert the results
        assert isinstance(remote_tools, list)
        assert len(remote_tools) > 0, "No tools were discovered from browsermcp"

        # Check that all items are of the correct type
        for tool in remote_tools:
            assert isinstance(tool, mcp_types.Tool)

        tool_names = [tool.name for tool in remote_tools]
        
        # Print the discovered tool names for informative test output
        logger.info(f"Discovered @browsermcp/mcp tools: {tool_names}")

    finally:
        # 6. Ensure the server connection and its subprocess are closed
        await server.close()
