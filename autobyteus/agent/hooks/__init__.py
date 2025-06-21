# file: autobyteus/autobyteus/agent/hooks/__init__.py
"""
Components for defining and running lifecycle hooks based on agent phase transitions.
"""
from .base_phase_hook import BasePhaseHook

__all__ = [
    "BasePhaseHook",
]
