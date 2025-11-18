"""Integration tests for the WebSocket-managed MCP server.

The toy WSS server (`autobyteus_mcps/wss_mcp_toy`) must be running locally
before executing this test. The default expects the endpoint to listen on
`wss://127.0.0.1:8765/mcp` with an allowed origin of `https://localhost` and
an untrusted, self-signed certificate (verification disabled). Override the
defaults via the environment variables documented below when running pytest.
"""

from __future__ import annotations

import os
import ssl

import pytest

from autobyteus.tools.mcp.server import WebsocketManagedMcpServer
from autobyteus.tools.mcp.types import WebsocketMcpServerConfig
from mcp import types as mcp_types

_WSS_URL_ENV = "WSS_MCP_URL"
_WSS_ORIGIN_ENV = "WSS_MCP_ORIGIN"
_WSS_VERIFY_ENV = "WSS_MCP_VERIFY_TLS"
_WSS_CA_FILE_ENV = "WSS_MCP_CA_FILE"
_WSS_CLIENT_CERT_ENV = "WSS_MCP_CLIENT_CERT"
_WSS_CLIENT_KEY_ENV = "WSS_MCP_CLIENT_KEY"

_DEFAULT_WSS_URL = "wss://127.0.0.1:8765/mcp"
_DEFAULT_WSS_ORIGIN = "https://localhost"


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_path(name: str) -> str | None:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else None


@pytest.mark.asyncio
async def test_websocket_managed_server_lists_and_calls_tools():
    """Verify WebsocketManagedMcpServer can enumerate and call tools."""

    target_url = os.environ.get(_WSS_URL_ENV, _DEFAULT_WSS_URL)
    origin = os.environ.get(_WSS_ORIGIN_ENV, _DEFAULT_WSS_ORIGIN)
    verify_tls = _env_bool(_WSS_VERIFY_ENV, default=False)

    config = WebsocketMcpServerConfig(
        server_id="toy-wss-server",
        url=target_url,
        origin=origin,
        headers={},
        verify_tls=verify_tls,
        ca_file=_env_path(_WSS_CA_FILE_ENV),
        client_cert=_env_path(_WSS_CLIENT_CERT_ENV),
        client_key=_env_path(_WSS_CLIENT_KEY_ENV),
    )

    server = WebsocketManagedMcpServer(config)

    try:
        try:
            tools = await server.list_remote_tools()
        except (ConnectionError, OSError, ssl.SSLError) as exc:
            pytest.skip(
                "WebSocket MCP server not reachable at "
                f"{target_url}. Start wss_mcp_toy locally or set {_WSS_URL_ENV}. Error: {exc}"
            )

        tool_names = {tool.name for tool in tools}
        assert tool_names == {"echo_text", "server_time"}

        echo_response = await server.call_tool("echo_text", {"text": "pytest", "uppercase": True})
        assert isinstance(echo_response, mcp_types.CallToolResult)
        assert echo_response.isError is False
        assert echo_response.structuredContent is None
        assert echo_response.content
        assert echo_response.content[0].text.lower() == "echo: pytest"

        time_response = await server.call_tool("server_time", {})
        assert isinstance(time_response, mcp_types.CallToolResult)
        assert time_response.isError is False
        assert time_response.structuredContent
        assert "iso8601" in time_response.structuredContent
        assert "epoch" in time_response.structuredContent
    finally:
        await server.close()
