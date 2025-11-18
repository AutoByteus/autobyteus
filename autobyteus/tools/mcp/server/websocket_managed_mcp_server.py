from __future__ import annotations

import asyncio
import logging
import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import ClientSession, types as mcp_types
from mcp.shared.message import SessionMessage
from pydantic import ValidationError
from websockets.asyncio.client import connect as ws_connect
from websockets.typing import Subprotocol

from .base_managed_mcp_server import BaseManagedMcpServer
from ..types import WebsocketMcpServerConfig

logger = logging.getLogger(__name__)

INITIALIZE_TIMEOUT = 10  # seconds


def _build_ssl_context(config: WebsocketMcpServerConfig) -> ssl.SSLContext | None:
    """Builds an SSL context when the target URL uses wss://."""
    if not config.url or not config.url.lower().startswith("wss://"):
        return None

    if config.verify_tls:
        context = ssl.create_default_context()
        if config.ca_file:
            context.load_verify_locations(cafile=config.ca_file)
    else:
        context = ssl._create_unverified_context()

    if config.client_cert:
        context.load_cert_chain(certfile=config.client_cert, keyfile=config.client_key)

    return context


def _normalize_subprotocols(config: WebsocketMcpServerConfig) -> list[Subprotocol]:
    """Ensures the MCP subprotocol is always negotiated."""
    provided = [proto for proto in config.subprotocols if proto]
    lowered = {proto.lower() for proto in provided}
    if "mcp" not in lowered:
        provided.append("mcp")
    return [Subprotocol(proto) for proto in provided]


@asynccontextmanager
async def _websocket_transport(
    config: WebsocketMcpServerConfig,
) -> AsyncGenerator[
    tuple[MemoryObjectReceiveStream[SessionMessage | Exception], MemoryObjectSendStream[SessionMessage]],
    None,
]:
    read_stream_writer, read_stream = anyio.create_memory_object_stream[SessionMessage | Exception](0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream[SessionMessage](0)

    headers = dict(config.headers)
    if not headers:
        headers = None

    connect_kwargs = {
        "origin": config.origin,
        "subprotocols": _normalize_subprotocols(config),
        "additional_headers": headers,
        "open_timeout": config.open_timeout,
        "ping_interval": config.ping_interval,
        "ping_timeout": config.ping_timeout,
        "ssl": _build_ssl_context(config),
    }
    # Remove None values so websockets uses library defaults
    connect_kwargs = {key: value for key, value in connect_kwargs.items() if value is not None}

    negotiated_protocols = [str(proto) for proto in connect_kwargs.get("subprotocols", [])]

    logger.debug(
        "Connecting to MCP WebSocket %s (subprotocols=%s, origin=%s)",
        config.url,
        negotiated_protocols,
        config.origin,
    )

    async with ws_connect(config.url, **connect_kwargs) as websocket:

        async def ws_reader():
            async with read_stream_writer:
                async for raw_message in websocket:
                    payload = raw_message.decode("utf-8") if isinstance(raw_message, bytes) else raw_message
                    try:
                        message = mcp_types.JSONRPCMessage.model_validate_json(payload)
                        await read_stream_writer.send(SessionMessage(message))
                    except ValidationError as exc:
                        await read_stream_writer.send(exc)

        async def ws_writer():
            async with write_stream_reader:
                async for session_message in write_stream_reader:
                    payload = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                    await websocket.send(payload)

        async with anyio.create_task_group() as tg:
            tg.start_soon(ws_reader)
            tg.start_soon(ws_writer)
            try:
                yield read_stream, write_stream
            finally:
                tg.cancel_scope.cancel()


class WebsocketManagedMcpServer(BaseManagedMcpServer):
    """Manages the lifecycle of a WebSocket-based MCP server connection."""

    def __init__(self, config: WebsocketMcpServerConfig):
        super().__init__(config)

    async def _create_client_session(self) -> ClientSession:
        config = cast(WebsocketMcpServerConfig, self._config)

        read_stream, write_stream = await self._exit_stack.enter_async_context(
            _websocket_transport(config)
        )
        session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

        try:
            await asyncio.wait_for(session.initialize(), timeout=INITIALIZE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error(
                "Timeout occurred while initializing WebSocket session for server '%s'.",
                self.server_id,
            )
            raise ConnectionError(
                f"Server '{self.server_id}' failed to initialize within the timeout period."
            ) from None

        logger.debug("ClientSession established and initialized for WebSocket server '%s'.", self.server_id)
        return session
