from autobyteus.utils.singleton import SingletonMeta
from autobyteus.events.event_manager import EventManager

class EventEmitter():
    def __init__(self):
        self.event_manager = EventManager()

    def subscribe(self, event, listener):
        self.event_manager.subscribe(event, listener)

    def unsubscribe(self, event, listener):
        self.event_manager.unsubscribe(event, listener)

    def emit(self, event, *args, **kwargs):
        self.event_manager.emit(event, *args, **kwargs)