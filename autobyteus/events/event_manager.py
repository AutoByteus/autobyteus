# File: autobyteus/events/event_manager.py

from autobyteus.events.event_types import EventType
from autobyteus.utils.singleton import SingletonMeta

class EventManager(metaclass=SingletonMeta):
    def __init__(self):
        self.listeners = {}

    def subscribe(self, event: EventType, listener):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(listener)

    def unsubscribe(self, event: EventType, listener):
        if event in self.listeners:
            self.listeners[event].remove(listener)

    def emit(self, event: EventType, *args, **kwargs):
        if event in self.listeners:
            for listener in self.listeners[event]:
                listener(*args, **kwargs)