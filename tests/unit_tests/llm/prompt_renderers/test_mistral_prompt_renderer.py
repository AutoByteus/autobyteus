import pytest

from autobyteus.llm.prompt_renderers.mistral_prompt_renderer import MistralPromptRenderer
from autobyteus.llm.utils.messages import (
    Message,
    MessageRole,
    ToolCallPayload,
    ToolCallSpec,
    ToolResultPayload,
)


@pytest.mark.asyncio
async def test_mistral_prompt_renderer_basic_messages():
    renderer = MistralPromptRenderer()
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
async def test_mistral_prompt_renderer_tool_payloads():
    renderer = MistralPromptRenderer()
    tool_args = {"query": "autobyteus"}
    tool_result = {"status": "ok"}
    messages = [
        Message(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_payload=ToolCallPayload(
                tool_calls=[ToolCallSpec(id="call_1", name="search", arguments=tool_args)]
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
    assert rendered == [
        {"role": "assistant", "content": "[TOOL_CALL] search {'query': 'autobyteus'}"},
        {"role": "user", "content": "[TOOL_RESULT] search {'status': 'ok'}"},
    ]
