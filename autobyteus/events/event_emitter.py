import uuid
import logging
from typing import Optional, Callable, Any

from autobyteus.events.event_manager import EventManager, Topic, Subscription
from autobyteus.events.event_types import EventType

logger = logging.getLogger(__name__)

class EventEmitter:
    def __init__(self):
        self.object_id = str(uuid.uuid4())
        self.event_manager = EventManager()

    def subscribe(self, event: EventType, listener: Callable):
        """Subscribe to an event globally, from any sender."""
        subscription = Subscription(subscriber_id=self.object_id, listener=listener)
        topic = Topic(event_type=event, sender_id=None)
        self.event_manager.subscribe(subscription, topic)

    def subscribe_from(self, sender: 'EventEmitter', event: EventType, listener: Callable):
        """Subscribe to an event ONLY from a specific sender."""
        subscription = Subscription(subscriber_id=self.object_id, listener=listener)
        sender_id = sender.object_id if sender and hasattr(sender, 'object_id') else None
        topic = Topic(event_type=event, sender_id=sender_id)
        self.event_manager.subscribe(subscription, topic)

    def unsubscribe(self, event: EventType, listener: Callable):
        """Unsubscribe a specific listener from a global event."""
        subscription = Subscription(subscriber_id=self.object_id, listener=listener)
        topic = Topic(event_type=event, sender_id=None)
        self.event_manager.unsubscribe(subscription, topic)

    def unsubscribe_from(self, sender: 'EventEmitter', event: EventType, listener: Callable):
        """Unsubscribe a specific listener from a specific sender."""
        subscription = Subscription(subscriber_id=self.object_id, listener=listener)
        sender_id = sender.object_id if sender and hasattr(sender, 'object_id') else None
        topic = Topic(event_type=event, sender_id=sender_id)
        self.event_manager.unsubscribe(subscription, topic)

    def unsubscribe_all_listeners(self):
        """
        Unsubscribes all listeners that THIS object instance has registered.
        The primary tool for guaranteed cleanup.
        """
        logger.debug(f"EventEmitter {self.object_id} is unsubscribing all its listeners.")
        self.event_manager.unsubscribe_all_for_subscriber(self.object_id)

    def emit(self, event: EventType, **kwargs: Any):
        """Emit an event originating from this object instance, with any payload."""
        self.event_manager.emit(event, origin_object_id=self.object_id, **kwargs)
