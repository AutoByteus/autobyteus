# file: autobyteus/autobyteus/agent/workspace/workspace_config.py
import logging
from typing import Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class WorkspaceConfig:
    """
    Configuration class for agent workspaces - a simple dictionary wrapper.
    Workspace implementations define their own default configurations internally
    and use this class to receive configuration overrides.
    """
    params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not isinstance(self.params, dict):
            raise TypeError("params must be a dictionary")
        
        logger.debug(f"WorkspaceConfig initialized with params keys: {list(self.params.keys())}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the WorkspaceConfig to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the configuration.
        """
        return self.params.copy()

    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> 'WorkspaceConfig':
        """
        Create a WorkspaceConfig instance from a dictionary.
        
        Args:
            config_data: Dictionary containing configuration parameters.
            
        Returns:
            WorkspaceConfig: New WorkspaceConfig instance.
        """
        if not isinstance(config_data, dict):
            raise TypeError("config_data must be a dictionary")
        
        return cls(params=config_data.copy())

    def merge(self, other: 'WorkspaceConfig') -> 'WorkspaceConfig':
        """
        Merge this WorkspaceConfig with another, with the other taking precedence.
        
        Args:
            other: WorkspaceConfig to merge with this one.
            
        Returns:
            WorkspaceConfig: New merged WorkspaceConfig instance.
        """
        if not isinstance(other, WorkspaceConfig):
            raise TypeError("Can only merge with another WorkspaceConfig instance")
        
        merged_params = self.params.copy()
        merged_params.update(other.params)
        
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
        return self.params.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration parameter.
        
        Args:
            key: The parameter key.
            value: The parameter value.
        """
        self.params[key] = value

    def update(self, params: Dict[str, Any]) -> None:
        """
        Update multiple configuration parameters.
        
        Args:
            params: Dictionary of parameters to update.
        """
        if not isinstance(params, dict):
            raise TypeError("params must be a dictionary")
        self.params.update(params)

    def __repr__(self) -> str:
        return f"WorkspaceConfig(params={self.params})"

    def __len__(self) -> int:
        return len(self.params)

    def __bool__(self) -> bool:
        return bool(self.params)
