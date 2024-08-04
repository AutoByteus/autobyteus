# File: autobyteus/events/event_emitter.py

from autobyteus.events.event_manager import EventManager
from autobyteus.events.event_types import EventType
from typing import Optional, Callable

class EventEmitter:
    def __init__(self):
        self.event_manager = EventManager()
        self._register_event_listeners()

    def _register_event_listeners(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, '_is_event_listener'):
                self.event_manager.subscribe(attr._event_type, attr, getattr(self, 'agent_id', None))

    def subscribe(self, event: EventType, listener: Callable, agent_id: Optional[str] = None):
        self.event_manager.subscribe(event, listener, agent_id)

    def unsubscribe(self, event: EventType, listener: Callable, agent_id: Optional[str] = None):
        self.event_manager.unsubscribe(event, listener, agent_id)

    def emit(self, event: EventType, agent_id: Optional[str] = None, *args, **kwargs):
        self.event_manager.emit(event, agent_id, *args, **kwargs)