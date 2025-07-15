# file: autobyteus/autobyteus/agent/workspace/workspace_config.py
import logging
import json
from typing import Dict, Any, Mapping
from collections.abc import Mapping as MappingABC

logger = logging.getLogger(__name__)

def _default_serializer(obj: Any) -> Any:
    """
    A robust serializer for objects that might not be JSON-serializable,
    ensuring a stable representation for hashing and comparison.
    """
    try:
        # For common un-serializable collection types, convert to a sorted list
        # to ensure a stable representation.
        if isinstance(obj, set):
            return sorted(list(obj))
        # For other objects, repr() is often a good choice for a unique,
        # and often reconstructible, string representation.
        return repr(obj)
    except Exception:
        # Fallback for any object that fails repr() or other serialization.
        return f"<unrepresentable object of type {type(obj).__name__}>"


class WorkspaceConfig:
    """
    An immutable, hashable configuration class for agent workspaces.

    This class stores workspace configuration parameters. It is immutable, meaning
    that methods like `set` or `update` return a new `WorkspaceConfig` instance
    rather than modifying the existing one.

    This immutability makes `WorkspaceConfig` instances hashable, allowing them to
    be used as dictionary keys for caching and reusing workspace instances.
    """
    _params: Dict[str, Any]
    _canonical_rep: str

    def __init__(self, params: Mapping[str, Any] = None):
        """
        Initializes the WorkspaceConfig.

        Args:
            params: A dictionary of configuration parameters. A copy is stored.
        """
        self._params = dict(params or {})
        
        # Pre-compute canonical representation for hashing and equality.
        try:
            self._canonical_rep = json.dumps(self._params, sort_keys=True, default=_default_serializer)
        except Exception as e:
            logger.error(f"Failed to create canonical representation for WorkspaceConfig: {e}", exc_info=True)
            # Fallback for extreme cases
            self._canonical_rep = repr(self._params)

        logger.debug(f"WorkspaceConfig initialized with params keys: {list(self._params.keys())}")

    def __hash__(self) -> int:
        return hash(self._canonical_rep)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkspaceConfig):
            return NotImplemented
        return self._canonical_rep == other._canonical_rep

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the WorkspaceConfig to a dictionary representation.
        
        Returns:
            Dict[str, Any]: A copy of the configuration parameters.
        """
        return self._params.copy()

    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> 'WorkspaceConfig':
        """
        Create a WorkspaceConfig instance from a dictionary.
        
        Args:
            config_data: Dictionary containing configuration parameters.
            
        Returns:
            A new, immutable WorkspaceConfig instance.
        """
        if not isinstance(config_data, dict):
            raise TypeError("config_data must be a dictionary")
        return cls(params=config_data)

    def merge(self, other: 'WorkspaceConfig') -> 'WorkspaceConfig':
        """
        Merge this WorkspaceConfig with another, with the other taking precedence.
        
        Args:
            other: WorkspaceConfig to merge with this one.
            
        Returns:
            A new, merged WorkspaceConfig instance.
        """
        if not isinstance(other, WorkspaceConfig):
            raise TypeError("Can only merge with another WorkspaceConfig instance")
        
        merged_params = self._params.copy()
        merged_params.update(other._params)
        return WorkspaceConfig(params=merged_params)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration parameter.
        
        Args:
            key: The parameter key.
            default: Default value if key doesn't exist.
            
        Returns:
            The parameter value or default.
        """
        return self._params.get(key, default)

    def set(self, key: str, value: Any) -> 'WorkspaceConfig':
        """
        Return a new WorkspaceConfig with a key set to a new value.
        
        Args:
            key: The parameter key.
            value: The parameter value.

        Returns:
            A new WorkspaceConfig instance with the updated parameter.
        """
        new_params = self._params.copy()
        new_params[key] = value
        return WorkspaceConfig(params=new_params)

    def update(self, params: Mapping[str, Any]) -> 'WorkspaceConfig':
        """
        Return a new WorkspaceConfig with multiple updated parameters.
        
        Args:
            params: Dictionary of parameters to update.
            
        Returns:
            A new WorkspaceConfig instance with the updated parameters.
        """
        if not isinstance(params, MappingABC):
            raise TypeError("params must be a mapping (e.g., a dictionary)")
        new_params = self._params.copy()
        new_params.update(params)
        return WorkspaceConfig(params=new_params)

    def __repr__(self) -> str:
        return f"WorkspaceConfig(params={self._params})"

    def __len__(self) -> int:
        return len(self._params)

    def __bool__(self) -> bool:
        return bool(self._params)
