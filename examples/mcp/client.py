import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

class MCPClient:
    def __init__(self):
        self.session = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server via stdio."""
        # Define server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None
        )

        # Establish stdio transport
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport

        # Create and initialize client session
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        print("Connected to server with tools:", [tool.name for tool in response.tools])

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call a tool on the server."""
        if not self.session:
            raise RuntimeError("Client not connected to server")
        result = await self.session.call_tool(tool_name, arguments)
        print(f"Tool '{tool_name}' result: {result.content[0].text}")

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        # Connect to the server
        await client.connect_to_server("calculator_server.py")

        # Call the 'add' tool
        await client.call_tool("add", {"a": 5, "b": 3})

    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())