import time

from autobyteus.llm.utils.messages import (
    Message,
    MessageRole,
    ToolCallPayload,
    ToolCallSpec,
    ToolResultPayload,
)
from autobyteus.memory.working_context_snapshot import WorkingContextSnapshot


def test_working_context_snapshot_append_order():
    snapshot = WorkingContextSnapshot()

    snapshot.append_user("Hello")
    snapshot.append_assistant("Hi there")
    snapshot.append_tool_calls(
        [ToolCallSpec(id="call_1", name="search", arguments={"q": "autobyteus"})]
    )
    snapshot.append_tool_result(
        tool_call_id="call_1",
        tool_name="search",
        tool_result={"ok": True},
        tool_error=None,
    )

    messages = snapshot.build_messages()
    assert [m.role for m in messages] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.ASSISTANT,
        MessageRole.TOOL,
    ]
    assert isinstance(messages[2].tool_payload, ToolCallPayload)
    assert isinstance(messages[3].tool_payload, ToolResultPayload)


def test_working_context_snapshot_reset_increments_epoch():
    snapshot = WorkingContextSnapshot()
    snapshot.append_user("First")
    initial_epoch = snapshot.epoch_id

    snapshot_messages = [
        Message(role=MessageRole.SYSTEM, content="System"),
        Message(role=MessageRole.USER, content="Snapshot user"),
    ]
    snapshot.reset(snapshot_messages, last_compaction_ts=123.0)

    assert snapshot.epoch_id == initial_epoch + 1
    assert snapshot.last_compaction_ts == 123.0
    messages = snapshot.build_messages()
    assert [m.role for m in messages] == [MessageRole.SYSTEM, MessageRole.USER]


def test_working_context_snapshot_metadata_defaults():
    snapshot = WorkingContextSnapshot()
    assert snapshot.epoch_id == 1
    assert snapshot.last_compaction_ts is None
