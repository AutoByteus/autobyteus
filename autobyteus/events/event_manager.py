from autobyteus.events.event_types import EventType
from autobyteus.utils.singleton import SingletonMeta
from typing import Dict, List, Callable, Optional

class EventManager(metaclass=SingletonMeta):
    def __init__(self):
        self.listeners: Dict[EventType, Dict[Optional[str], List[Callable]]] = {}

    def subscribe(self, event: EventType, listener: Callable, agent_id: Optional[str] = None):
        if event not in self.listeners:
            self.listeners[event] = {}
        if agent_id not in self.listeners[event]:
            self.listeners[event][agent_id] = []
        self.listeners[event][agent_id].append(listener)

    def unsubscribe(self, event: EventType, listener: Callable, agent_id: Optional[str] = None):
        if event in self.listeners and agent_id in self.listeners[event]:
            self.listeners[event][agent_id].remove(listener)
            if not self.listeners[event][agent_id]:
                del self.listeners[event][agent_id]

    def emit(self, event: EventType, agent_id: Optional[str] = None, *args, **kwargs):
        if event in self.listeners:
            # Include agent_id in kwargs
            updated_kwargs = {'agent_id': agent_id, **kwargs}
            
            if agent_id is not None and agent_id in self.listeners[event]:
                for listener in self.listeners[event][agent_id]:
                    listener(*args, **updated_kwargs)
            if None in self.listeners[event]:  # Global listeners
                for listener in self.listeners[event][None]:
                    listener(*args, **updated_kwargs)