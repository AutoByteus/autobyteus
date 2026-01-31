from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.tool_interaction import ToolInteractionStatus
from autobyteus.memory.tool_interaction_builder import build_tool_interactions


def _trace(**kwargs):
    return RawTraceItem(
        id=kwargs.get("id", "rt_1"),
        ts=kwargs.get("ts", 1.0),
        turn_id=kwargs.get("turn_id", "turn_1"),
        seq=kwargs.get("seq", 1),
        trace_type=kwargs["trace_type"],
        content=kwargs.get("content", ""),
        source_event=kwargs.get("source_event", "Test"),
        tool_name=kwargs.get("tool_name"),
        tool_call_id=kwargs.get("tool_call_id"),
        tool_args=kwargs.get("tool_args"),
        tool_result=kwargs.get("tool_result"),
        tool_error=kwargs.get("tool_error"),
    )


def test_build_tool_interactions_success():
    traces = [
        _trace(trace_type="tool_call", tool_call_id="call_1", tool_name="search", tool_args={"q": "a"}, seq=1),
        _trace(trace_type="tool_result", tool_call_id="call_1", tool_name="search", tool_result={"ok": True}, seq=2),
    ]

    interactions = build_tool_interactions(traces)
    assert len(interactions) == 1
    interaction = interactions[0]
    assert interaction.tool_call_id == "call_1"
    assert interaction.tool_name == "search"
    assert interaction.arguments == {"q": "a"}
    assert interaction.result == {"ok": True}
    assert interaction.error is None
    assert interaction.status == ToolInteractionStatus.SUCCESS


def test_build_tool_interactions_error():
    traces = [
        _trace(trace_type="tool_call", tool_call_id="call_2", tool_name="write_file", tool_args={"p": "x"}, seq=1),
        _trace(trace_type="tool_result", tool_call_id="call_2", tool_name="write_file", tool_error="boom", seq=2),
    ]

    interactions = build_tool_interactions(traces)
    assert len(interactions) == 1
    interaction = interactions[0]
    assert interaction.tool_call_id == "call_2"
    assert interaction.status == ToolInteractionStatus.ERROR
    assert interaction.error == "boom"


def test_build_tool_interactions_pending_when_no_result():
    traces = [
        _trace(trace_type="tool_call", tool_call_id="call_3", tool_name="read_file", tool_args={"p": "x"}, seq=1),
    ]

    interactions = build_tool_interactions(traces)
    assert len(interactions) == 1
    interaction = interactions[0]
    assert interaction.tool_call_id == "call_3"
    assert interaction.status == ToolInteractionStatus.PENDING
