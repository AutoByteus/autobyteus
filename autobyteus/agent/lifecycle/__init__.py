# file: autobyteus/agent/lifecycle/__init__.py
"""
Lifecycle module provides simplified extension points for agent lifecycle events.
Replaces the more complex Status Hooks system with a simple processor pattern.
"""
from autobyteus.agent.lifecycle.events import LifecycleEvent
from autobyteus.agent.lifecycle.base_processor import BaseLifecycleEventProcessor

__all__ = [
    "LifecycleEvent",
    "BaseLifecycleEventProcessor",
]
