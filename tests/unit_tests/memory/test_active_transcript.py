import time

from autobyteus.llm.utils.messages import (
    Message,
    MessageRole,
    ToolCallPayload,
    ToolCallSpec,
    ToolResultPayload,
)
from autobyteus.memory.active_transcript import ActiveTranscript


def test_active_transcript_append_order():
    transcript = ActiveTranscript()

    transcript.append_user("Hello")
    transcript.append_assistant("Hi there")
    transcript.append_tool_calls(
        [ToolCallSpec(id="call_1", name="search", arguments={"q": "autobyteus"})]
    )
    transcript.append_tool_result(
        tool_call_id="call_1",
        tool_name="search",
        tool_result={"ok": True},
        tool_error=None,
    )

    messages = transcript.build_messages()
    assert [m.role for m in messages] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.ASSISTANT,
        MessageRole.TOOL,
    ]
    assert isinstance(messages[2].tool_payload, ToolCallPayload)
    assert isinstance(messages[3].tool_payload, ToolResultPayload)


def test_active_transcript_reset_increments_epoch():
    transcript = ActiveTranscript()
    transcript.append_user("First")
    initial_epoch = transcript.epoch_id

    snapshot = [
        Message(role=MessageRole.SYSTEM, content="System"),
        Message(role=MessageRole.USER, content="Snapshot user"),
    ]
    transcript.reset(snapshot, last_compaction_ts=123.0)

    assert transcript.epoch_id == initial_epoch + 1
    assert transcript.last_compaction_ts == 123.0
    messages = transcript.build_messages()
    assert [m.role for m in messages] == [MessageRole.SYSTEM, MessageRole.USER]


def test_active_transcript_metadata_defaults():
    transcript = ActiveTranscript()
    assert transcript.epoch_id == 1
    assert transcript.last_compaction_ts is None
