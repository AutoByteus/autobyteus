# file: autobyteus/autobyteus/agent/tool_invocation.py
import uuid
import hashlib
import json
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from autobyteus.agent.events import ToolResultEvent

logger = logging.getLogger(__name__)

class ToolInvocation:
    def __init__(self, name: Optional[str] = None, arguments: Optional[Dict[str, Any]] = None, id: Optional[str] = None):
        """
        Represents a tool invocation request.

        Args:
            name: The name of the tool to be invoked.
            arguments: A dictionary of arguments for the tool.
            id: Optional. A unique identifier for this tool invocation.
                If None, a deterministic ID will be generated based on the tool name and arguments.
        """
        self.name: Optional[str] = name
        self.arguments: Optional[Dict[str, Any]] = arguments
        
        if id is not None:
            self.id: str = id
        elif self.name is not None and self.arguments is not None:
            self.id: str = self._generate_deterministic_id(self.name, self.arguments)
        else:
            # Fallback to UUID if name/args are not provided during init, though this is an edge case.
            self.id: str = f"call_{uuid.uuid4().hex}"

    @staticmethod
    def _generate_deterministic_id(name: str, arguments: Dict[str, Any]) -> str:
        """
        Generates a deterministic ID for the tool invocation based on its content.
        """
        # Create a canonical representation of the arguments
        # sort_keys=True ensures that the order of keys doesn't change the hash
        # ensure_ascii=False is critical for cross-language compatibility with JS
        canonical_args = json.dumps(arguments, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        
        # Create a string to hash
        hash_string = f"{name}:{canonical_args}"
        
        # --- ADDED LOGGING ---
        logger.debug(f"Generating tool invocation ID from hash_string: '{hash_string}'")
        
        # Use SHA256 for a robust hash
        sha256_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
        
        # Prepend a prefix for clarity and use the full hash.
        return f"call_{sha256_hash}"

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
