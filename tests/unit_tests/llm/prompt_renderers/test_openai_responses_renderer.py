import json
import pytest

from autobyteus.llm.prompt_renderers.openai_responses_renderer import OpenAIResponsesRenderer
from autobyteus.llm.utils.messages import (
    Message,
    MessageRole,
    ToolCallPayload,
    ToolCallSpec,
    ToolResultPayload,
)


@pytest.mark.asyncio
async def test_openai_responses_renderer_basic_messages():
    renderer = OpenAIResponsesRenderer()
    messages = [
        Message(role=MessageRole.SYSTEM, content="System"),
        Message(role=MessageRole.USER, content="Hello"),
    ]

    rendered = await renderer.render(messages)
    assert rendered == [
        {"type": "message", "role": "system", "content": "System"},
        {"type": "message", "role": "user", "content": "Hello"},
    ]


@pytest.mark.asyncio
async def test_openai_responses_renderer_tool_payloads_degrade_to_text():
    renderer = OpenAIResponsesRenderer()
    tool_args = {"path": "README.md"}
    tool_result = {"status": "ok"}
    messages = [
        Message(
            role=MessageRole.ASSISTANT,
            tool_payload=ToolCallPayload(
                tool_calls=[ToolCallSpec(id="call_9", name="read_file", arguments=tool_args)]
            ),
        ),
        Message(
            role=MessageRole.TOOL,
            tool_payload=ToolResultPayload(
                tool_call_id="call_9",
                tool_name="read_file",
                tool_result=tool_result,
            ),
        ),
    ]

    rendered = await renderer.render(messages)
    assert rendered == [
        {
            "type": "message",
            "role": "assistant",
            "content": f"[TOOL_CALL] read_file {json.dumps(tool_args, ensure_ascii=True)}",
        },
        {
            "type": "message",
            "role": "user",
            "content": f"[TOOL_RESULT] read_file {json.dumps(tool_result, ensure_ascii=True)}",
        },
    ]
