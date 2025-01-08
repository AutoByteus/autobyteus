
import uuid
from typing import Optional, Callable
from autobyteus.events.event_manager import EventManager
from autobyteus.events.event_types import EventType

class EventEmitter:
    def __init__(self):
        # Give each emitter a unique ID to differentiate event sources
        self.object_id = str(uuid.uuid4())
        self.event_manager = EventManager()
        self._register_event_listeners()

    def _register_event_listeners(self):
        """
        Internally register any methods decorated with @event_listener.
        """
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, '_is_event_listener'):
                self.event_manager.subscribe(
                    attr._event_type,
                    attr,
                    getattr(self, 'object_id', None)
                )

    def subscribe(self, event: EventType, listener: Callable):
        """
        Subscribe to an event globally (regardless of who the object is).
        Equivalent to objectA.subscribe(eventType, objectA.eventHandler).
        """
        self.event_manager.subscribe(event, listener, target_object_id=None)

    def subscribe_from(self, sender: 'EventEmitter', event: EventType, listener: Callable):
        """
        Subscribe to an event originating from a specific sender (another EventEmitter).
        Equivalent to objectA.subscribe(objectB, eventType, objectA.eventHandler).
        """
        if sender is not None and hasattr(sender, 'object_id'):
            self.event_manager.subscribe(event, listener, target_object_id=sender.object_id)
        else:
            # If invalid sender is provided, default to global subscription
            self.event_manager.subscribe(event, listener, target_object_id=None)

    def unsubscribe(self, event: EventType, listener: Callable):
        """
        Unsubscribe from an event globally.
        """
        self.event_manager.unsubscribe(event, listener, target_object_id=None)

    def unsubscribe_from(self, sender: 'EventEmitter', event: EventType, listener: Callable):
        """
        Unsubscribe from an event that originates from a specific sender.
        """
        if sender is not None and hasattr(sender, 'object_id'):
            self.event_manager.unsubscribe(event, listener, target_object_id=sender.object_id)

    def emit(self, event: EventType, target: Optional['EventEmitter'] = None, *args, **kwargs):
        """
        Emit an event from this specific emitter (identified by self.object_id).

        If 'target' is provided, this performs a direct object-to-object emission
        that only notifies the 'target' about this event (bypassing global listeners).

        :param event: The event type to emit
        :param target: If specified, will notify only the target emitter's subscriptions
                       for this event (object-to-object direct emit).
        :param args: Additional positional arguments for listeners.
        :param kwargs: Additional keyword arguments for listeners.
        """
        if target:
            self.event_manager.emit(event, origin_object_id=self.object_id, target_object_id=target.object_id, *args, **kwargs)
        else:
            self.event_manager.emit(event, origin_object_id=self.object_id, *args, **kwargs)
