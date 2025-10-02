# file: autobyteus/autobyteus/agent/processor_option.py
"""
Defines common data transfer objects for agent component options.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessorOption:
    """A data class representing a processor option for configuration."""
    name: str
    is_mandatory: bool

@dataclass(frozen=True)
class HookOption:
    """A data class representing a hook option for configuration."""
    name: str
    is_mandatory: bool
