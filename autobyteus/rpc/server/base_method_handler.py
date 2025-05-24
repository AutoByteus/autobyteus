# file: autobyteus/autobyteus/rpc/server/base_method_handler.py
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, TYPE_CHECKING

from autobyteus.rpc.protocol import ProtocolMessage

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent # Changed from AgentRuntime to Agent

logger = logging.getLogger(__name__)

class BaseMethodHandler(ABC):
    """
    Abstract base class for handlers of specific RPC methods on the Agent Server.
    """

    @abstractmethod
    async def handle(self,
                     request_id: Optional[str],
                     params: Optional[Dict[str, Any]],
                     agent: 'Agent') -> ProtocolMessage: # Changed from runtime: AgentRuntime to agent: Agent
        """
        Handles an RPC method call.

        Args:
            request_id: The ID of the incoming request message. Used for the response.
            params: The parameters provided with the RPC method call.
            agent: The Agent instance being served. This provides access to the
                   agent's public API, context, queues, status, etc.

        Returns:
            A ProtocolMessage representing the response (success or error) to be sent
            back to the client.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

