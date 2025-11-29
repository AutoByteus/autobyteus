import pytest

from autobyteus.agent.events.agent_input_event_queue_manager import (
    AgentInputEventQueueManager,
)
from autobyteus.agent.events.agent_events import (
    PendingToolInvocationEvent,
    ToolResultEvent,
)
from autobyteus.agent.tool_invocation import ToolInvocation


class _DummyTask:
    """Lightweight stand‑in for asyncio.Task used in the monkeypatched wait()."""

    def __init__(self, name, result_obj):
        self._name = name
        self._result_obj = result_obj

    def get_name(self):
        return self._name

    def result(self):
        return self._result_obj

    def done(self):
        return True

    def cancel(self):
        # No‑op for compatibility with cleanup logic
        return None


@pytest.mark.asyncio
async def test_get_next_input_event_buffers_without_inverting_tool_order(monkeypatch):
    """
    When multiple queues are ready, results are buffered and selected by priority
    without re-inserting to the tail, so tool call order is preserved.
    """
    mgr = AgentInputEventQueueManager()

    # Intended FIFO order: T1 then T2
    await mgr.tool_invocation_request_queue.put(
        PendingToolInvocationEvent(
            tool_invocation=ToolInvocation("tool_1", {}, id="t1")
        )
    )
    await mgr.tool_invocation_request_queue.put(
        PendingToolInvocationEvent(
            tool_invocation=ToolInvocation("tool_2", {}, id="t2")
        )
    )

    # Competing queue has a ready result event
    await mgr.tool_result_input_queue.put(
        ToolResultEvent(tool_name="other", result="ok")
    )

    async def fake_wait(tasks, return_when):
        """
        Force a deterministic done list: result first, then tool invocation.
        Items are consumed once and buffered; no tail requeue should occur.
        """
        res_item = await mgr.tool_result_input_queue.get()
        inv_item = await mgr.tool_invocation_request_queue.get()
        done = [
            _DummyTask("tool_result_input_queue", res_item),
            _DummyTask("tool_invocation_request_queue", inv_item),
        ]
        pending = []
        return done, pending

    monkeypatch.setattr(
        "autobyteus.agent.events.agent_input_event_queue_manager.asyncio.wait",
        fake_wait,
    )

    # Consume one event; tool call should be returned first (priority) and order preserved.
    evt = await mgr.get_next_input_event()
    assert evt is not None
    qname, event = evt
    assert qname == "tool_invocation_request_queue"
    assert event.tool_invocation.id == "t1"

    # Next call should return the buffered result, not disturb tool order.
    evt2 = await mgr.get_next_input_event()
    assert evt2 is not None
    qname2, event2 = evt2
    assert qname2 == "tool_result_input_queue"
    assert isinstance(event2, ToolResultEvent)

    # Remaining tool call keeps original order.
    evt3 = await mgr.get_next_input_event()
    assert evt3 is not None
    _qname3, event3 = evt3
    assert event3.tool_invocation.id == "t2"


@pytest.mark.asyncio
async def test_get_next_input_event_preserves_fifo_when_only_tool_queue_ready():
    """Baseline: with a single ready queue, FIFO order is retained."""
    mgr = AgentInputEventQueueManager()

    await mgr.tool_invocation_request_queue.put(
        PendingToolInvocationEvent(
            tool_invocation=ToolInvocation("tool_1", {}, id="t1")
        )
    )
    await mgr.tool_invocation_request_queue.put(
        PendingToolInvocationEvent(
            tool_invocation=ToolInvocation("tool_2", {}, id="t2")
        )
    )

    # No other queues have items; normal path should not reorder.
    evt1 = await mgr.get_next_input_event()
    evt2 = await mgr.get_next_input_event()

    assert evt1 is not None
    assert evt2 is not None

    _qname1, e1 = evt1
    _qname2, e2 = evt2

    assert e1.tool_invocation.id == "t1"
    assert e2.tool_invocation.id == "t2"
