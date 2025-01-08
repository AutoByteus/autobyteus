
import pytest
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType

@pytest.fixture
def emitter():
    return EventEmitter()

def test_init(emitter):
    assert hasattr(emitter, 'event_manager')
    assert hasattr(emitter, 'object_id')

def test_subscribe(emitter):
    collected = []

    def dummy_listener(**kwargs):
        collected.append(True)

    emitter.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)

    # Manually emit to confirm subscription
    emitter.emit(EventType.TOOL_EXECUTION_STARTED)
    assert len(collected) == 1

    # Check that the subscription is stored under target_object_id=None
    assert dummy_listener in emitter.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED][None]

def test_unsubscribe(emitter):
    collected = []

    def dummy_listener(**kwargs):
        collected.append(True)

    emitter.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
    emitter.emit(EventType.TOOL_EXECUTION_STARTED)
    assert len(collected) == 1

    emitter.unsubscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
    emitter.emit(EventType.TOOL_EXECUTION_STARTED)
    # Should not be called again
    assert len(collected) == 1

    # Ensure the listener is removed from the global (None) listeners
    assert (
        EventType.TOOL_EXECUTION_STARTED not in emitter.event_manager.listeners
        or None not in emitter.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED]
        or dummy_listener not in emitter.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED][None]
    )

def test_subscribe_from():
    emitter_a = EventEmitter()
    emitter_b = EventEmitter()
    result = []

    def dummy_listener(data, **kwargs):
        result.append(data)

    # Subscribe emitter_a to events from emitter_b
    emitter_a.subscribe_from(emitter_b, EventType.TOOL_EXECUTION_COMPLETED, dummy_listener)

    # Emitting on emitter_a should NOT trigger dummy_listener
    emitter_a.emit(EventType.TOOL_EXECUTION_COMPLETED, data="no-receive")
    assert len(result) == 0

    # Emitting on emitter_b should trigger dummy_listener
    emitter_b.emit(EventType.TOOL_EXECUTION_COMPLETED, data="yes-receive")
    assert len(result) == 1
    assert result[0] == "yes-receive"

def test_unsubscribe_from():
    emitter_a = EventEmitter()
    emitter_b = EventEmitter()
    result = []

    def dummy_listener(data, **kwargs):
        result.append(data)

    emitter_a.subscribe_from(emitter_b, EventType.TOOL_EXECUTION_COMPLETED, dummy_listener)
    emitter_b.emit(EventType.TOOL_EXECUTION_COMPLETED, data="event1")
    assert result == ["event1"]

    emitter_a.unsubscribe_from(emitter_b, EventType.TOOL_EXECUTION_COMPLETED, dummy_listener)
    emitter_b.emit(EventType.TOOL_EXECUTION_COMPLETED, data="event2")
    assert result == ["event1"]

def test_emit(emitter):
    result = []

    def dummy_listener(value, **kwargs):
        result.append(value)

    emitter.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
    emitter.emit(EventType.TOOL_EXECUTION_STARTED, value="test")
    assert result == ["test"]

class ListenerClass:
    def __init__(self):
        self.received_events = []

    def listener_method(self, data, **kwargs):
        self.received_events.append(data)

def test_subscribe_with_class_method(emitter):
    listener_instance = ListenerClass()
    emitter.subscribe(EventType.TOOL_EXECUTION_STARTED, listener_instance.listener_method)

    emitter.emit(EventType.TOOL_EXECUTION_STARTED, data="event1")
    emitter.emit(EventType.TOOL_EXECUTION_STARTED, data="event2")

    assert listener_instance.received_events == ["event1", "event2"]
    assert listener_instance.listener_method in emitter.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED][None]

def test_unsubscribe_with_class_method(emitter):
    listener_instance = ListenerClass()
    emitter.subscribe(EventType.TOOL_EXECUTION_STARTED, listener_instance.listener_method)

    emitter.emit(EventType.TOOL_EXECUTION_STARTED, data="event1")
    assert listener_instance.received_events == ["event1"]

    emitter.unsubscribe(EventType.TOOL_EXECUTION_STARTED, listener_instance.listener_method)
    emitter.emit(EventType.TOOL_EXECUTION_STARTED, data="event2")
    assert listener_instance.received_events == ["event1"]  # No change after unsubscribe

    # Ensure the listener method is removed from the global listeners
    assert (
        EventType.TOOL_EXECUTION_STARTED not in emitter.event_manager.listeners
        or None not in emitter.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED]
        or listener_instance.listener_method not in emitter.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED][None]
    )

def test_subscribe_from_with_class_method():
    emitter_a = EventEmitter()
    emitter_b = EventEmitter()
    listener_instance = ListenerClass()

    emitter_a.subscribe_from(emitter_b, EventType.TOOL_EXECUTION_COMPLETED, listener_instance.listener_method)

    # Emitting on emitter_a should NOT trigger the listener
    emitter_a.emit(EventType.TOOL_EXECUTION_COMPLETED, data="no-receive")
    assert listener_instance.received_events == []

    # Emitting on emitter_b should trigger the listener
    emitter_b.emit(EventType.TOOL_EXECUTION_COMPLETED, data="yes-receive")
    assert listener_instance.received_events == ["yes-receive"]

def test_unsubscribe_from_with_class_method():
    emitter_a = EventEmitter()
    emitter_b = EventEmitter()
    listener_instance = ListenerClass()

    emitter_a.subscribe_from(emitter_b, EventType.TOOL_EXECUTION_COMPLETED, listener_instance.listener_method)
    emitter_b.emit(EventType.TOOL_EXECUTION_COMPLETED, data="event1")
    assert listener_instance.received_events == ["event1"]

    emitter_a.unsubscribe_from(emitter_b, EventType.TOOL_EXECUTION_COMPLETED, listener_instance.listener_method)
    emitter_b.emit(EventType.TOOL_EXECUTION_COMPLETED, data="event2")
    assert listener_instance.received_events == ["event1"]  # No change after unsubscribe

def test_independent_instance_listeners():
    emitter_a = EventEmitter()
    emitter_b = EventEmitter()
    listener_a = ListenerClass()
    listener_b = ListenerClass()

    # Subscribe listener_a only to emitter_a
    emitter_a.subscribe_from(emitter_a, EventType.TOOL_EXECUTION_STARTED, listener_a.listener_method)

    # Subscribe listener_b only to emitter_b
    emitter_b.subscribe_from(emitter_b, EventType.TOOL_EXECUTION_STARTED, listener_b.listener_method)

    # Emit event from emitter_a
    emitter_a.emit(EventType.TOOL_EXECUTION_STARTED, data="event_a")

    # Emit event from emitter_b
    emitter_b.emit(EventType.TOOL_EXECUTION_STARTED, data="event_b")

    # Verify that listener_a received only 'event_a'
    assert listener_a.received_events == ["event_a"]

    # Verify that listener_b received only 'event_b'
    assert listener_b.received_events == ["event_b"]

    # Additionally, ensure that each listener is registered under its respective emitter's target_object_id
    assert listener_a.listener_method in emitter_a.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED][emitter_a.object_id]
    assert listener_b.listener_method in emitter_b.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED][emitter_b.object_id]

    # And confirm that neither is in the other's subscription group
    assert listener_a.listener_method not in emitter_a.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED].get(emitter_b.object_id, [])
    assert listener_b.listener_method not in emitter_b.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED].get(emitter_a.object_id, [])

def test_direct_object_to_object_emit():
    emitter_a = EventEmitter()
    emitter_b = EventEmitter()

    received_from_b_only = []

    def only_listen_to_b(data, **kwargs):
        received_from_b_only.append(data)

    # Subscribe emitter_a to only events that come from emitter_b
    emitter_a.subscribe_from(emitter_b, EventType.TOOL_EXECUTION_STARTED, only_listen_to_b)

    # Direct object-to-object emit from b to a
    emitter_b.emit(EventType.TOOL_EXECUTION_STARTED, emitter_a, data="direct_message")

    # Since this is a direct emit, we expect the subscription logic to still treat emitter_b as origin.
    # That means emitter_a's 'subscribe_from(emitter_b...)' should receive it.
    assert received_from_b_only == ["direct_message"]

    # If emitter_b emits normally, it should do the same thing
    emitter_b.emit(EventType.TOOL_EXECUTION_STARTED, data="normal_emit")
    assert received_from_b_only == ["direct_message", "normal_emit"]

def test_subscribe_and_subscribe_from_together():
    """
    In this test, we subscribe globally (subscribe) to an event
    and also subscribe_from a specific emitter. We verify that:
      - On normal emit, both the global listener and the origin-specific listener are triggered.
      - On direct object-to-object emit, only the origin-specific listener is triggered (global is skipped).
    """
    emitter_a = EventEmitter()
    emitter_b = EventEmitter()

    global_collected = []
    from_b_collected = []

    def global_listener(data, **kwargs):
        global_collected.append(data)

    def from_b_listener(data, **kwargs):
        from_b_collected.append(data)

    # emitter_a subscribes globally to TOOL_EXECUTION_STARTED
    emitter_a.subscribe(EventType.TOOL_EXECUTION_STARTED, global_listener)

    # emitter_a also subscribes specifically to events from emitter_b
    emitter_a.subscribe_from(emitter_b, EventType.TOOL_EXECUTION_STARTED, from_b_listener)

    # 1) Normal emit on emitter_b => both global and from_b should fire
    emitter_b.emit(EventType.TOOL_EXECUTION_STARTED, data="normal_emit")
    assert global_collected == ["normal_emit"], "Global listener should receive normal emits from any emitter."
    assert from_b_collected == ["normal_emit"], "Origin-specific listener from emitter_b should receive normal emits from emitter_b."

    # 2) Direct emit from emitter_b to emitter_a => only from_b_listener should fire, global listener is skipped
    emitter_b.emit(EventType.TOOL_EXECUTION_STARTED, emitter_a, data="direct_emit")
    assert global_collected == ["normal_emit"], "Global listener remains unchanged, as direct emit skips global."
    assert from_b_collected == ["normal_emit", "direct_emit"], (
        "Origin-specific listener should receive direct object-to-object emits from emitter_b."
    )
