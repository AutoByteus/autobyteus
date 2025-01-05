
import functools
from autobyteus.events.event_types import EventType
from autobyteus.events.event_emitter import EventEmitter

def publish_event(event_type: EventType):
    """
    Decorator to publish an event after successful function execution.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if isinstance(self, EventEmitter):
                # Emit the event from this emitter instance
                self.emit(event_type, result=result)
            return result
        return wrapper
    return decorator

def event_listener(event_type: EventType):
    """
    Decorator to mark a method as an event listener.
    """
    def decorator(func):
        func._is_event_listener = True
        func._event_type = event_type
        return func
    return decorator
