# File: autobyteus/events/event_emitter.py

from autobyteus.events.event_manager import EventManager
from autobyteus.events.event_types import EventType
class EventEmitter:
    def __init__(self):
        self.event_manager = EventManager()
        self._register_event_listeners()

    def _register_event_listeners(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, '_is_event_listener'):
                self.event_manager.subscribe(attr._event_type, attr)

    def subscribe(self, event: EventType, listener):
        self.event_manager.subscribe(event, listener)

    def unsubscribe(self, event: EventType, listener):
        self.event_manager.unsubscribe(event, listener)

    def emit(self, event: EventType, *args, **kwargs):
        self.event_manager.emit(event, *args, **kwargs)