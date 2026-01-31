import json
import pytest

from autobyteus.llm.prompt_renderers.openai_chat_renderer import OpenAIChatRenderer
from autobyteus.llm.utils.messages import (
    Message,
    MessageRole,
    ToolCallPayload,
    ToolCallSpec,
    ToolResultPayload,
)


@pytest.mark.asyncio
async def test_openai_chat_renderer_basic_messages():
    renderer = OpenAIChatRenderer()
    messages = [
        Message(role=MessageRole.SYSTEM, content="System"),
        Message(role=MessageRole.USER, content="Hello"),
    ]

    rendered = await renderer.render(messages)
    assert rendered == [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Hello"},
    ]


@pytest.mark.asyncio
async def test_openai_chat_renderer_tool_payloads():
    renderer = OpenAIChatRenderer()
    tool_args = {"query": "autobyteus"}
    tool_result = {"status": "ok"}
    messages = [
        Message(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_payload=ToolCallPayload(
                tool_calls=[
                    ToolCallSpec(id="call_1", name="search", arguments=tool_args)
                ]
            ),
        ),
        Message(
            role=MessageRole.TOOL,
            tool_payload=ToolResultPayload(
                tool_call_id="call_1",
                tool_name="search",
                tool_result=tool_result,
            ),
        ),
    ]

    rendered = await renderer.render(messages)
    assert rendered[0]["role"] == "assistant"
    assert rendered[0]["content"] is None
    assert rendered[0]["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "search",
                "arguments": json.dumps(tool_args, ensure_ascii=True),
            },
        }
    ]

    assert rendered[1]["role"] == "tool"
    assert rendered[1]["tool_call_id"] == "call_1"
    assert rendered[1]["content"] == json.dumps(tool_result, ensure_ascii=True)
