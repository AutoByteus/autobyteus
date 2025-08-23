from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class MultimediaConfig:
    """
    Configuration for multimedia generation, using a flexible dictionary for parameters.
    """
    params: Dict[str, Any] = field(default_factory=dict)

    def merge_with(self, override_config: Optional['MultimediaConfig']):
        """
        Merges parameters from an override config into this one.
        """
        if override_config and override_config.params:
            self.params.update(override_config.params)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultimediaConfig':
        """
        Creates a MultimediaConfig instance from a dictionary of parameters.
        """
        return cls(params=data if data is not None else {})

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns the configuration parameters as a dictionary.
        """
        return self.params
