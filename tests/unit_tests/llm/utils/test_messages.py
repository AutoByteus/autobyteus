import pytest

from autobyteus.llm.utils.messages import (
    Message,
    MessageRole,
    ToolCallPayload,
    ToolCallSpec,
    ToolResultPayload,
)


def test_message_role_includes_tool():
    assert MessageRole.TOOL.value == "tool"


def test_assistant_tool_calls_message_to_dict():
    tool_calls = [
        ToolCallSpec(id="call_1", name="search", arguments={"q": "autobyteus"})
    ]
    message = Message(
        role=MessageRole.ASSISTANT,
        content=None,
        tool_payload=ToolCallPayload(tool_calls=tool_calls),
    )

    data = message.to_dict()
    assert data["role"] == "assistant"
    assert data["tool_payload"] == {
        "tool_calls": [{"id": "call_1", "name": "search", "arguments": {"q": "autobyteus"}}]
    }


def test_tool_result_message_to_dict():
    message = Message(
        role=MessageRole.TOOL,
        tool_payload=ToolResultPayload(
            tool_call_id="call_1",
            tool_name="search",
            tool_result={"ok": True},
            tool_error=None,
        ),
    )

    data = message.to_dict()
    assert data["role"] == "tool"
    assert data["tool_payload"] == {
        "tool_call_id": "call_1",
        "tool_name": "search",
        "tool_result": {"ok": True},
        "tool_error": None,
    }
