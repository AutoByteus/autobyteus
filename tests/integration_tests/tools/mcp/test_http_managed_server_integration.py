"""Integration tests for the HTTP-managed MCP server.

The test assumes a streamable HTTP MCP endpoint (for example, the
`streamable_http_mcp_toy` project) is already running locally before pytest is
invoked. Override the target URL via the `STREAMABLE_HTTP_MCP_URL` environment
variable if you bind it somewhere other than `http://127.0.0.1:8764/mcp`.
"""

from __future__ import annotations

import os

import pytest

from autobyteus.tools.mcp.server import HttpManagedMcpServer
from autobyteus.tools.mcp.types import StreamableHttpMcpServerConfig
from mcp import types as mcp_types

_STREAMABLE_HTTP_URL_ENV = "STREAMABLE_HTTP_MCP_URL"
_DEFAULT_STREAMABLE_HTTP_URL = "http://127.0.0.1:8764/mcp"


@pytest.mark.asyncio
async def test_http_managed_server_lists_and_calls_tools():
    """Verify HttpManagedMcpServer can enumerate and call tools over HTTP."""

    target_url = os.environ.get(_STREAMABLE_HTTP_URL_ENV, _DEFAULT_STREAMABLE_HTTP_URL)

    config = StreamableHttpMcpServerConfig(
        server_id="streamable-http-toy",
        url=target_url,
        headers={},
    )

    server = HttpManagedMcpServer(config)

    try:
        try:
            tools = await server.list_remote_tools()
        except (ConnectionError, OSError) as exc:
            pytest.skip(
                f"Streamable HTTP MCP server not reachable at {target_url}. "
                f"Start streamable_http_mcp_toy locally or set {_STREAMABLE_HTTP_URL_ENV}. Error: {exc}"
            )

        tool_names = {tool.name for tool in tools}
        assert tool_names == {"echo_text", "server_time"}

        echo_response = await server.call_tool("echo_text", {"text": "pytest"})
        assert isinstance(echo_response, mcp_types.CallToolResult)
        assert echo_response.isError is False
        assert echo_response.structuredContent and echo_response.structuredContent.get("result") == "echo: pytest"

        time_response = await server.call_tool("server_time", {})
        assert isinstance(time_response, mcp_types.CallToolResult)
        assert time_response.isError is False
        assert time_response.structuredContent
        assert "iso8601" in time_response.structuredContent
        assert "epoch" in time_response.structuredContent
    finally:
        await server.close()
