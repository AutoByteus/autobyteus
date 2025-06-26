import logging
import asyncio
import inspect
import functools
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional, Any

from autobyteus.events.event_types import EventType
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

# --- Final, Semantically Clear Data Structures ---

@dataclass(frozen=True)
class Topic:
    """A clear, hashable data object representing what to subscribe to."""
    event_type: EventType
    sender_id: Optional[str] = None

@dataclass(frozen=True)
class Subscription:
    """A clear, hashable data object representing a single subscription."""
    subscriber_id: str
    listener: Callable

class SubscriberList:
    """Manages all Subscriptions for a single Topic in a thread-safe way."""
    def __init__(self):
        # The key is subscriber_id. The value is a list of all subscriptions
        # made by that subscriber for THIS topic.
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._lock = threading.Lock()

    def add(self, subscription: Subscription):
        with self._lock:
            # Avoid adding the exact same listener function multiple times for the same subscriber
            if not any(sub.listener is subscription.listener for sub in self._subscriptions[subscription.subscriber_id]):
                self._subscriptions[subscription.subscriber_id].append(subscription)

    def remove_subscriber(self, subscriber_id: str):
        """Removes all subscriptions for a given subscriber ID from this topic."""
        with self._lock:
            self._subscriptions.pop(subscriber_id, None)

    def remove_specific(self, subscriber_id: str, listener: Callable):
        """Removes a specific subscription matching the listener function."""
        with self._lock:
            if subscriber_id in self._subscriptions:
                self._subscriptions[subscriber_id] = [
                    sub for sub in self._subscriptions[subscriber_id]
                    if sub.listener is not listener
                ]
                if not self._subscriptions[subscriber_id]:
                    del self._subscriptions[subscriber_id]

    def get_all_listeners(self) -> List[Callable]:
        with self._lock:
            all_listeners = []
            for sub_list in self._subscriptions.values():
                for sub in sub_list:
                    all_listeners.append(sub.listener)
            return all_listeners
            
    def is_empty(self) -> bool:
        with self._lock:
            return not self._subscriptions

# --- The Final, Intelligent EventManager ---

class EventManager(metaclass=SingletonMeta):
    def __init__(self):
        self._topics: Dict[Topic, SubscriberList] = defaultdict(SubscriberList)
        self._lock = threading.Lock()

    def subscribe(self, subscription: Subscription, topic: Topic):
        """Subscribes a listener to a topic using clear objects."""
        self._topics[topic].add(subscription)
    
    def unsubscribe(self, subscription: Subscription, topic: Topic):
        """Unsubscribes a specific listener from a specific topic."""
        if topic in self._topics:
            self._topics[topic].remove_specific(subscription.subscriber_id, subscription.listener)
            if self._topics[topic].is_empty():
                 with self._lock:
                    self._topics.pop(topic, None)

    def unsubscribe_all_for_subscriber(self, subscriber_id: str):
        """Atomically removes all subscriptions made by a specific subscriber."""
        with self._lock:
            for topic in list(self._topics.keys()):
                self._topics[topic].remove_subscriber(subscriber_id)
                if self._topics[topic].is_empty():
                    del self._topics[topic]

    def _invoke_listener(self, listener: Callable, **available_kwargs: Any):
        actual_callable = listener
        if isinstance(listener, functools.partial):
            actual_callable = listener.func

        try:
            sig = inspect.signature(actual_callable)
            params = sig.parameters
        except (ValueError, TypeError):
            params = {}
            has_kwargs = True
        else:
             has_kwargs = any(p.kind == p.VAR_KEYWORD for p in params.values())

        if has_kwargs:
            final_args_to_pass = available_kwargs
        else:
            final_args_to_pass = {
                name: available_kwargs[name] for name in params if name in available_kwargs
            }
        
        if inspect.iscoroutinefunction(actual_callable):
            asyncio.create_task(listener(**final_args_to_pass))
        else:
            listener(**final_args_to_pass)

    def emit(self, event_type: EventType, origin_object_id: Optional[str] = None, **kwargs: Any):
        # FIX: Added 'event_type' to the dictionary passed to listeners.
        available_kwargs_for_listeners = {"event_type": event_type, "object_id": origin_object_id, **kwargs}
        
        targeted_topic = Topic(event_type, origin_object_id)
        global_topic = Topic(event_type, None)

        listeners_to_call: List[Callable] = []
        if targeted_topic in self._topics:
            listeners_to_call.extend(self._topics[targeted_topic].get_all_listeners())
        if global_topic in self._topics:
            listeners_to_call.extend(self._topics[global_topic].get_all_listeners())
        
        for listener_cb in listeners_to_call:
            try:
                self._invoke_listener(listener_cb, **available_kwargs_for_listeners)
            except Exception as e:
                logger.error(f"Error preparing to invoke listener {getattr(listener_cb, '__name__', 'unknown')} for event {event_type.name}: {e}", exc_info=True)
