# file: autobyteus/tests/unit_tests/agent/events/test_event_store.py
from autobyteus.agent.events.event_store import AgentEventStore
from autobyteus.agent.events.agent_events import AgentReadyEvent


def test_append_creates_envelope_and_increments_sequence():
    store = AgentEventStore(agent_id="agent-123")
    event = AgentReadyEvent()

    envelope = store.append(event, correlation_id="corr-1", caused_by_event_id="cause-0")

    assert envelope.event is event
    assert envelope.event_type == "AgentReadyEvent"
    assert envelope.agent_id == "agent-123"
    assert envelope.correlation_id == "corr-1"
    assert envelope.caused_by_event_id == "cause-0"
    assert envelope.sequence == 0
    assert isinstance(envelope.timestamp, float)

    second = store.append(AgentReadyEvent())
    assert second.sequence == 1


def test_all_events_returns_copy():
    store = AgentEventStore(agent_id="agent-xyz")
    store.append(AgentReadyEvent())
    store.append(AgentReadyEvent())

    events = store.all_events()
    assert len(events) == 2

    events.clear()
    assert len(store.all_events()) == 2
