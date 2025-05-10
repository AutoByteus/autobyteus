# file: autobyteus/autobyteus/tools/mcp_remote_tool.py
import logging
from typing import Any, Dict

from autobyteus.tools.base_tool import BaseTool
import mcp

logger = logging.getLogger(__name__)

class McpRemoteTool(BaseTool):
    """
    A tool that executes remote tool calls on an MCP (Model Context Protocol) server.
    """
    def __init__(self, name: str, description: str, connection_params: Dict[str, Any]):
        """
        Initializes the McpRemoteTool.

        Args:
            name: The unique name/identifier of the tool (e.g., 'McpRemoteTool').
            description: A human-readable description of the tool's purpose.
            connection_params: A dictionary containing MCP server connection details
                              (e.g., {'host': 'localhost', 'port': 5000}).

        Raises:
            ValueError: If name, description, or connection_params are invalid.
        """
        if not name or not isinstance(name, str):
            raise ValueError("McpRemoteTool requires a non-empty string 'name'.")
        if not description or not isinstance(description, str):
            raise ValueError(f"McpRemoteTool '{name}' requires a non-empty string 'description'.")
        if not isinstance(connection_params, dict) or not connection_params:
            raise ValueError(f"McpRemoteTool '{name}' requires a non-empty dictionary for 'connection_params'.")

        super().__init__(name, description)
        self.connection_params = connection_params
        logger.debug(f"McpRemoteTool initialized with name '{self.name}' and connection_params: {self.connection_params}")

    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Executes the remote tool call on the MCP server.

        Args:
            args: A dictionary containing the tool name and parameters to pass to the MCP server
                  (e.g., {'tool_name': 'do_mcp_analysis', 'params': {...}}).

        Returns:
            The result of the tool execution, typically a dictionary or string.

        Raises:
            ValueError: If args is invalid or missing required fields.
            RuntimeError: If the MCP server connection or tool execution fails.
        """
        if not isinstance(args, dict) or 'tool_name' not in args:
            logger.error(f"Invalid arguments for McpRemoteTool '{self.name}': 'tool_name' is required.")
            raise ValueError("McpRemoteTool requires a dictionary with a 'tool_name' key.")

        tool_name = args['tool_name']
        params = args.get('params', {})
        logger.info(f"Executing McpRemoteTool '{self.name}' with tool_name '{tool_name}' and params: {params}")

        try:
            # Step 17: Establish connection to MCP server
            client = mcp.stdio_client(self.connection_params)
            logger.debug(f"Connected to MCP server with connection_params: {self.connection_params}")

            # Step 19: Create client session
            session = client.ClientSession()
            logger.debug(f"Created MCP client session for tool '{tool_name}'")

            # Step 20: Initialize session
            session.initialize()
            logger.debug(f"Initialized MCP session for tool '{tool_name}'")

            # Step 21: Call the remote tool
            result = session.call_tool(tool_name, params)
            logger.info(f"Successfully executed MCP tool '{tool_name}' with result: {result}")

            return result

        except Exception as e:
            logger.error(f"Failed to execute McpRemoteTool '{self.name}' for tool '{tool_name}': {str(e)}")
            raise RuntimeError(f"McpRemoteTool execution failed: {str(e)}")