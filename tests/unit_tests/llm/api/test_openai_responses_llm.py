# file: autobyteus/tests/unit_tests/llm/api/test_openai_responses_llm.py
import types
import pytest

from autobyteus.llm.api.openai_responses_llm import OpenAIResponsesLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.user_message import LLMUserMessage

from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_reasoning_item import ResponseReasoningItem


def _build_llm(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return OpenAIResponsesLLM(
        model=LLMModel["gpt-5.2"],
        llm_config=LLMConfig(),
        api_key_env_var="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
    )


def test_extract_output_content_with_reasoning_summary(monkeypatch):
    llm = _build_llm(monkeypatch)

    message = ResponseOutputMessage.model_validate({
        "id": "msg1",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [
            {"type": "output_text", "text": "Hello", "annotations": []}
        ],
    })
    reasoning = ResponseReasoningItem.model_validate({
        "id": "r1",
        "type": "reasoning",
        "summary": [
            {"type": "summary_text", "text": "Because."}
        ],
    })

    content, summary = llm._extract_output_content([message, reasoning])
    assert content == "Hello"
    assert summary == "Because."


def test_normalize_tools_converts_openai_schema(monkeypatch):
    llm = _build_llm(monkeypatch)
    tools = [{
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a file",
            "parameters": {"type": "object", "properties": {}},
        },
    }]

    normalized = llm._normalize_tools(tools)
    assert normalized == [{
        "type": "function",
        "name": "write_file",
        "description": "Write a file",
        "parameters": {"type": "object", "properties": {}},
    }]


@pytest.mark.asyncio
async def test_streaming_emits_reasoning_and_tool_calls(monkeypatch):
    llm = _build_llm(monkeypatch)

    events = [
        types.SimpleNamespace(
            type="response.output_text.delta",
            delta="Hi",
            output_index=0,
            item_id="item1",
            content_index=0,
            sequence_number=1,
        ),
        types.SimpleNamespace(
            type="response.reasoning_summary_text.delta",
            delta="Thinking",
            output_index=0,
            item_id="item2",
            summary_index=0,
            sequence_number=2,
        ),
        types.SimpleNamespace(
            type="response.output_item_added",
            output_index=0,
            sequence_number=3,
            item=types.SimpleNamespace(
                type="function_call",
                call_id="call_1",
                name="write_file",
            ),
        ),
        types.SimpleNamespace(
            type="response.function_call_arguments.delta",
            output_index=0,
            item_id="item3",
            delta='{"path":"hello.txt"}',
            sequence_number=4,
        ),
        types.SimpleNamespace(
            type="response.completed",
            sequence_number=5,
            response=types.SimpleNamespace(
                usage=types.SimpleNamespace(
                    input_tokens=1,
                    output_tokens=2,
                    total_tokens=3,
                )
            ),
        ),
    ]

    llm.client.responses.create = lambda **kwargs: iter(events)

    user_message = LLMUserMessage(content="Hello")
    content_chunks = []
    reasoning_chunks = []
    tool_call_deltas = []
    completed = None

    async for chunk in llm._stream_user_message_to_llm(user_message):
        if chunk.content:
            content_chunks.append(chunk.content)
        if chunk.reasoning:
            reasoning_chunks.append(chunk.reasoning)
        if chunk.tool_calls:
            tool_call_deltas.extend(chunk.tool_calls)
        if chunk.is_complete:
            completed = chunk

    assert "".join(content_chunks) == "Hi"
    assert "".join(reasoning_chunks) == "Thinking"
    assert tool_call_deltas
    assert completed is not None
    assert completed.usage is not None
