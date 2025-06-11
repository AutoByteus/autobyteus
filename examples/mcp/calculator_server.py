from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Calculator Server")

# Define a tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

# Run the server with stdio transport
if __name__ == "__main__":
    mcp.run(transport="stdio")