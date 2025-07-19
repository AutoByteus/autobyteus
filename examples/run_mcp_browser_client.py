# file: autobyteus/examples/run_mcp_browser_client.py
"""
This example script demonstrates how to create a standalone MCP client in Python
to connect to and interact with the Browser MCP server.

This script uses only the 'mcp' library and standard Python libraries,
intentionally avoiding the 'autobyteus' framework abstractions.
This approach is useful for understanding the low-level communication
with an MCP server.

The script will:
1.  Define the parameters to launch the Browser MCP server (`npx @browsermcp/mcp@latest`).
2.  Start the server process and establish an stdio transport.
3.  Initialize an MCP client session.
4.  List the available tools from the server.
5.  Call the 'open_page' tool to open a website.
6.  Call the 'get_page_content' tool to retrieve the page's text.
7.  Properly clean up the session and server process.
"""

import asyncio
import logging
import sys
import json
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger("mcp_browser_client")


class MCPBrowserClient:
    """
    A client for interacting with a Browser MCP server over stdio.
    """

    def __init__(self):
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self.page_id: str | None = None

    async def connect(self):
        """
        Starts the browser MCP server and connects to it.
        """
        logger.info("Defining server parameters for Browser MCP...")
        # These parameters specify how to run the MCP server.
        # This is the same command used by the `run_browser_agent.py` example.
        server_params = StdioServerParameters(
            command="npx",
            args=["@browsermcp/mcp@latest"],
            env=None,
        )

        logger.info(f"Starting server with command: '{server_params.command} {' '.join(server_params.args)}'")

        # `stdio_client` is a context manager that starts the process
        # and provides reader/writer streams for communication.
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport

        logger.info("Server process started. Establishing MCP session...")

        # `ClientSession` is another context manager that handles the MCP protocol.
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))

        # The initialize handshake must be performed after connection.
        await self.session.initialize()
        logger.info("MCP session initialized successfully.")

        # Let's see what tools the server offers.
        response = await self.session.list_tools()
        tool_names = [tool.name for tool in response.tools]
        logger.info(f"Connected to server. Available tools: {tool_names}")

    async def call_tool(self, tool_name: str, **kwargs):
        """
        A wrapper to call a tool on the server and print the result.
        """
        if not self.session:
            raise RuntimeError("Client not connected. Call connect() first.")

        logger.info(f"Calling tool '{tool_name}' with arguments: {kwargs}")
        try:
            result = await self.session.call_tool(tool_name, kwargs)
            logger.info(f"Tool '{tool_name}' executed successfully.")

            # The result content is a list of blocks. For many tools, it's a single text block.
            if result.content and hasattr(result.content[0], 'text'):
                tool_output = result.content[0].text
                logger.info(f"--> Result from '{tool_name}':\n{tool_output[:500]}...")
                return tool_output
            else:
                logger.info(f"--> Result from '{tool_name}' has no text content: {result.content}")
                return result.content
        except Exception as e:
            logger.error(f"An error occurred while calling tool '{tool_name}': {e}", exc_info=True)
            raise

    async def cleanup(self):
        """
        Closes the session and stops the server process.
        The AsyncExitStack handles this automatically.
        """
        logger.info("Cleaning up resources and closing server connection...")
        await self.exit_stack.aclose()
        logger.info("Cleanup complete.")

    async def run_demo_flow(self):
        """
        Executes a simple workflow: open a page, get its content, and close it.
        """
        try:
            # 1. Open a page
            open_page_result = await self.call_tool("open_page", url="https://www.google.com/search?q=mcp+protocol")

            # The 'open_page' tool returns a JSON string with the pageId.
            # We need to parse it to use in subsequent calls.
            if not isinstance(open_page_result, str):
                logger.error(f"Expected a string from 'open_page', but got {type(open_page_result)}")
                return

            try:
                page_info = json.loads(open_page_result)
                self.page_id = page_info.get("pageId")
                if not self.page_id:
                    logger.error("Could not find 'pageId' in the result from 'open_page'.")
                    return
                logger.info(f"Successfully opened page. Page ID: {self.page_id}")
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Failed to parse pageId from 'open_page' result: {e}")
                return

            # 2. Get the page content
            # Add a small delay for the page to potentially load dynamic content.
            logger.info("Waiting for 2 seconds before getting content...")
            await asyncio.sleep(2)

            await self.call_tool("get_page_content", pageId=self.page_id)

            # 3. Close the page
            await self.call_tool("close_page", pageId=self.page_id)
            logger.info(f"Page {self.page_id} closed.")

        except Exception as e:
            logger.error(f"An error occurred during the demo flow: {e}")


async def main():
    """
    Main function to run the MCP Browser Client.
    """
    logger.info("--- Starting Standalone MCP Browser Client Example ---")
    client = MCPBrowserClient()
    try:
        await client.connect()
        await client.run_demo_flow()
    finally:
        await client.cleanup()
    logger.info("--- Standalone MCP Browser Client Example Finished ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script interrupted by user. Exiting.")

