# file: autobyteus/autobyteus/rpc/transport_type.py
from enum import Enum

class TransportType(str, Enum):
    """
    Defines the transport mechanisms supported for RPC communication.
    """
    STDIO = "stdio"
    SSE = "sse"  # Server-Sent Events over HTTP

    def __str__(self) -> str:
        return self.value

