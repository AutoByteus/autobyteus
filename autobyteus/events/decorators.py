import functools
from typing import Callable, Any, TypeVar, cast
from autobyteus.events.event_types import EventType
from autobyteus.events.event_emitter import EventEmitter

F = TypeVar('F', bound=Callable[..., Any])

def publish_event(event_type: EventType) -> Callable[[F], F]:
    """
    Decorator to publish an event after successful function execution.

    Args:
        event_type: The type of event to publish

    Returns:
        A decorator function that wraps the original method
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = func(self, *args, **kwargs)
            if isinstance(self, EventEmitter):
                # Emit the event from this emitter instance
                self.emit(event_type, result=result)
            return result
        return cast(F, wrapper)
    return decorator

def event_listener(event_type: EventType) -> Callable[[F], F]:
    """
    Decorator to mark a method as an event listener.

    Args:
        event_type: The type of event to listen for

    Returns:
        A decorator function that marks the method as an event listener
    """
    def decorator(func: F) -> F:
        func._is_event_listener = True  # type: ignore
        func._event_type = event_type   # type: ignore
        return func
    return decorator
