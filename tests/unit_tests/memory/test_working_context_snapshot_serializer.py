import json

from autobyteus.llm.utils.messages import Message, MessageRole, ToolCallPayload, ToolCallSpec, ToolResultPayload
from autobyteus.memory.working_context_snapshot import WorkingContextSnapshot
from autobyteus.memory.working_context_snapshot_serializer import (
    WorkingContextSnapshotSerializer,
)


def test_serializer_round_trip_with_tool_payloads():
    snapshot = WorkingContextSnapshot()
    snapshot.append_message(Message(role=MessageRole.SYSTEM, content="System"))
    snapshot.append_message(Message(role=MessageRole.USER, content="Hello"))
    snapshot.append_message(
        Message(
            role=MessageRole.ASSISTANT,
            content="Hi",
            reasoning_content="Because",
            image_urls=["img://1"],
            audio_urls=["aud://1"],
            video_urls=["vid://1"],
        )
    )
    snapshot.append_message(
        Message(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_payload=ToolCallPayload(
                tool_calls=[ToolCallSpec(id="call_1", name="search", arguments={"q": "abc"})]
            ),
        )
    )
    snapshot.append_message(
        Message(
            role=MessageRole.TOOL,
            content=None,
            tool_payload=ToolResultPayload(
                tool_call_id="call_1",
                tool_name="search",
                tool_result={"ok": True},
                tool_error=None,
            ),
        )
    )

    metadata = {"agent_id": "agent_1", "schema_version": 1}
    payload = WorkingContextSnapshotSerializer.serialize(snapshot, metadata)
    assert WorkingContextSnapshotSerializer.validate(payload)

    restored_snapshot, restored_meta = WorkingContextSnapshotSerializer.deserialize(payload)
    assert restored_meta["agent_id"] == "agent_1"
    messages = restored_snapshot.build_messages()
    assert [m.role for m in messages] == [
        MessageRole.SYSTEM,
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.ASSISTANT,
        MessageRole.TOOL,
    ]
    assert messages[2].reasoning_content == "Because"
    assert messages[2].image_urls == ["img://1"]
    assert isinstance(messages[3].tool_payload, ToolCallPayload)
    assert isinstance(messages[4].tool_payload, ToolResultPayload)


def test_serializer_handles_non_json_tool_result():
    class Weird:
        def __str__(self) -> str:
            return "<weird>"

    snapshot = WorkingContextSnapshot()
    snapshot.append_message(
        Message(
            role=MessageRole.TOOL,
            content=None,
            tool_payload=ToolResultPayload(
                tool_call_id="call_2",
                tool_name="weird",
                tool_result=Weird(),
                tool_error=None,
            ),
        )
    )

    payload = WorkingContextSnapshotSerializer.serialize(
        snapshot,
        {"agent_id": "agent_2", "schema_version": 1},
    )
    # Should be JSON-serializable after normalization
    json.dumps(payload)


def test_serializer_validate_rejects_missing_fields():
    payload = {"schema_version": 1, "messages": []}
    assert not WorkingContextSnapshotSerializer.validate(payload)
