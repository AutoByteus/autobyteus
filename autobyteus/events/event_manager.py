from autobyteus.events.event_types import EventType
from autobyteus.utils.singleton import SingletonMeta
from typing import Dict, List, Callable, Optional, Any
from collections import defaultdict
import asyncio # ADDED
import inspect # ADDED
import functools # ADDED for checking partials

class EventError(Exception):
    """Base exception class for event-related errors."""
    pass

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
        if listener not in self.listeners[event][target_object_id]: # Avoid duplicate subscriptions
            self.listeners[event][target_object_id].append(listener)

    def unsubscribe(self, event: EventType, listener: Callable, target_object_id: Optional[str] = None):
        """
        Unsubscribe a listener from a specific event/target_object_id combination.
        If target_object_id is None, it targets the global subscription group for that event.
        """
        if event in self.listeners and target_object_id in self.listeners[event]:
            try:
                self.listeners[event][target_object_id].remove(listener)
                if not self.listeners[event][target_object_id]: # pragma: no cover
                    del self.listeners[event][target_object_id]
            except ValueError: # pragma: no cover
                # Listener not found, ignore silently or log
                pass 

    def _invoke_listener(self, listener: Callable, *args, **kwargs):
        """
        Helper to invoke a listener, creating a task if it's a coroutine function.
        """
        actual_callable_to_inspect = listener
        if isinstance(listener, functools.partial):
            actual_callable_to_inspect = listener.func
            
        if inspect.iscoroutinefunction(actual_callable_to_inspect) or \
           inspect.isasyncgenfunction(actual_callable_to_inspect):
            asyncio.create_task(listener(*args, **kwargs))
        else:
            # For synchronous listeners, execute directly.
            # If a synchronous listener itself returns a coroutine (not common for event handlers),
            # that coroutine would also not be awaited here and would cause a warning.
            # This fix primarily addresses listeners that are `async def`.
            listener(*args, **kwargs)


    def emit(self, event: EventType, origin_object_id: Optional[str] = None, target_object_id: Optional[str] = None, *args, **kwargs):
        """
        Emit an event.
        If 'target_object_id' is provided in the call to EventEmitter.emit(target=...), 
        it attempts a more direct notification pathway. The interpretation of this pathway
        is that listeners subscribed specifically TO THE ORIGIN (sender) are notified.
        If 'target_object_id' is NOT provided by EventEmitter.emit(target=...), 
        then listeners subscribed to the ORIGIN (sender) AND global listeners are notified.
        
        Note: The original comment about `target_object_id` in `EventManager.emit` was slightly
        ambiguous. The behavior implemented here aligns with `EventEmitter.subscribe_from(sender, ...)`
        where listeners subscribe to events *from* a specific `sender` (which is `origin_object_id` here).
        A true "direct message only to target" would require listeners to subscribe against the *target's* ID
        or a different mechanism.
        """
        if event not in self.listeners:
            return

        updated_kwargs = {"object_id": origin_object_id, **kwargs}

        # Determine which sets of listeners to notify.
        # Listeners are stored keyed by the ID of the object they want to hear *from* (or None for global).

        listeners_to_call: List[Callable] = []

        if target_object_id is not None:
            # This case corresponds to emitter.emit(event, target=some_other_emitter)
            # It implies a more focused emission. Per current EventEmitter.emit and EventManager.subscribe_from,
            # this notifies listeners who subscribed *from the origin_object_id*.
            # It does NOT mean "only call listeners on the target_object_id".
            # The 'target_object_id' parameter in EventManager.emit is perhaps confusingly named
            # in this context if one expects it to filter listeners TO the target.
            # It currently acts as a flag to *not* call global listeners.
            if origin_object_id is not None and origin_object_id in self.listeners[event]:
                listeners_to_call.extend(self.listeners[event][origin_object_id])
        else:
            # Standard broadcast: notify those listening to this specific origin, and global listeners.
            if origin_object_id is not None and origin_object_id in self.listeners[event]:
                listeners_to_call.extend(self.listeners[event][origin_object_id])
            
            if None in self.listeners[event]: # Global listeners for this event type
                # Avoid adding duplicates if a listener is somehow in both global and specific
                for l in self.listeners[event][None]:
                    if l not in listeners_to_call:
                        listeners_to_call.extend(self.listeners[event][None])
        
        for listener_cb in listeners_to_call:
            try:
                self._invoke_listener(listener_cb, *args, **updated_kwargs)
            except Exception as e: # pragma: no cover
                # Log error but continue notifying other listeners
                logging.getLogger(__name__).error(f"Error invoking event listener {getattr(listener_cb, '__name__', 'unknown')} for event {event.name}: {e}", exc_info=True)

