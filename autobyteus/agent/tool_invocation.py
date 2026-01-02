# file: autobyteus/autobyteus/agent/tool_invocation.py
import logging
from typing import Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from autobyteus.agent.events import ToolResultEvent

logger = logging.getLogger(__name__)

class ToolInvocation:
    def __init__(self, name: str, arguments: Dict[str, Any], id: str):
        """
        Represents a tool invocation request.

        Args:
            name: The name of the tool to be invoked.
            arguments: A dictionary of arguments for the tool.
            id: Required. A unique identifier for this tool invocation.
        """
        if not id:
            raise ValueError("ToolInvocation requires a non-empty id.")
        if not name:
            raise ValueError("ToolInvocation requires a non-empty name.")
        if arguments is None:
            raise ValueError("ToolInvocation requires arguments.")

        self.name: str = name
        self.arguments: Dict[str, Any] = arguments
        self.id: str = id

    def is_valid(self) -> bool:
        """
        Checks if the tool invocation has a name and arguments.
        The 'id' is always present (auto-generated if not provided).
        """
        return self.name is not None and self.arguments is not None

    def __repr__(self) -> str:
        return (f"ToolInvocation(id='{self.id}', name='{self.name}', "
                f"arguments={self.arguments})")


@dataclass
class ToolInvocationTurn:
    """
    A data class to encapsulate the state of a multi-tool invocation turn.
    Its existence in the agent's state signifies that a multi-tool turn is active.
    """
    invocations: List[ToolInvocation]
    results: List['ToolResultEvent'] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Checks if all expected tool results have been collected."""
        return len(self.results) >= len(self.invocations)
