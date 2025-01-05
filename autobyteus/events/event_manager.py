
from autobyteus.events.event_types import EventType
from autobyteus.utils.singleton import SingletonMeta
from typing import Dict, List, Callable, Optional

class EventManager(metaclass=SingletonMeta):
    def __init__(self):
        # listeners[event_type][target_object_id] = list of callbacks
        self.listeners: Dict[EventType, Dict[Optional[str], List[Callable]]] = {}

    def subscribe(self, event: EventType, listener: Callable, target_object_id: Optional[str] = None):
        """
        Subscribe a listener to a specific event from a given target_object_id.
        If target_object_id is None, the subscription is global.
        """
        if event not in self.listeners:
            self.listeners[event] = {}
        if target_object_id not in self.listeners[event]:
            self.listeners[event][target_object_id] = []
        self.listeners[event][target_object_id].append(listener)

    def unsubscribe(self, event: EventType, listener: Callable, target_object_id: Optional[str] = None):
        """
        Unsubscribe a listener from a specific event/target_object_id combination.
        If target_object_id is None, it targets the global subscription group for that event.
        """
        if event in self.listeners and target_object_id in self.listeners[event]:
            self.listeners[event][target_object_id].remove(listener)
            if not self.listeners[event][target_object_id]:
                del self.listeners[event][target_object_id]

    def emit(self, event: EventType, origin_object_id: Optional[str] = None, target_object_id: Optional[str] = None, *args, **kwargs):
        """
        Emit an event. By default, this notifies:
          1) All listeners subscribed to the specific 'origin_object_id' (if any).
          2) All global listeners (subscribed with target_object_id=None).

        If 'target_object_id' is provided, the event is dispatched ONLY
        to the listeners keyed by the origin_object_id. Global listeners
        are skipped, but the origin object subscribers are notified.
        
        :param event: The event type to emit.
        :param origin_object_id: The ID of the object emitting this event (sender).
        :param target_object_id: If specified, indicates a direct object-to-object emit,
                                 meaning only listeners subscribed under origin_object_id
                                 should be notified (skipping global).
        :param args: Positional arguments to pass to the listeners.
        :param kwargs: Keyword arguments to pass to the listeners.
        """
        if event not in self.listeners:
            return

        # Include sender info in kwargs
        updated_kwargs = {"object_id": origin_object_id, **kwargs}

        if target_object_id is not None:
            # Direct object-to-object emit
            # The subscription is keyed by the ORIGIN object_id (since we used subscribe_from(sender, ...)).
            if origin_object_id in self.listeners[event]:
                for listener in self.listeners[event][origin_object_id]:
                    listener(*args, **updated_kwargs)
            return

        # Otherwise, standard emit (no explicit target)
        # First, notify listeners specifically subscribed to origin_object_id
        if origin_object_id is not None and origin_object_id in self.listeners[event]:
            for listener in self.listeners[event][origin_object_id]:
                listener(*args, **updated_kwargs)

        # Then, notify global (None) listeners
        if None in self.listeners[event]:
            for listener in self.listeners[event][None]:
                listener(*args, **updated_kwargs)
