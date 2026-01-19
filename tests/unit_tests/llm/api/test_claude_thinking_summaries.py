# file: autobyteus/tests/unit_tests/llm/api/test_claude_thinking_summaries.py
"""
Unit tests for Claude extended thinking summaries.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from autobyteus.llm.api.claude_llm import ClaudeLLM, _build_thinking_param, _split_claude_content_blocks
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.user_message import LLMUserMessage


def _make_model():
    return LLMModel(
        name="claude-test",
        value="claude-test-v1",
        provider=LLMProvider.ANTHROPIC,
        llm_class=ClaudeLLM,
        canonical_name="claude-test",
    )


def test_build_thinking_param_enabled():
    params = {"thinking_enabled": True, "thinking_budget_tokens": 2048}
    thinking = _build_thinking_param(params)
    assert thinking == {"type": "enabled", "budget_tokens": 2048}


def test_split_claude_content_blocks():
    blocks = [
        SimpleNamespace(type="thinking", thinking="Thought summary."),
        SimpleNamespace(type="text", text="Final answer."),
    ]
    content, reasoning = _split_claude_content_blocks(blocks)
    assert content == "Final answer."
    assert reasoning == "Thought summary."


@pytest.mark.asyncio
async def test_send_user_message_includes_thinking_and_returns_reasoning():
    mock_client = MagicMock()
    mock_client.messages = MagicMock()

    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking="Thought summary."),
            SimpleNamespace(type="text", text="Final answer."),
        ],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    mock_client.messages.create.return_value = response

    with patch("autobyteus.llm.api.claude_llm.ClaudeLLM.initialize", return_value=mock_client):
        llm = ClaudeLLM(
            model=_make_model(),
            llm_config=LLMConfig(extra_params={"thinking_enabled": True, "thinking_budget_tokens": 2048}),
        )

        result = await llm._send_user_message_to_llm(LLMUserMessage(content="hello"))

        assert result.content == "Final answer."
        assert result.reasoning == "Thought summary."
        assert llm.messages[-1].reasoning_content == "Thought summary."

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 2048}


@pytest.mark.asyncio
async def test_stream_emits_thinking_deltas():
    class MockStream:
        def __init__(self, events, final_message):
            self._events = events
            self._final_message = final_message

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            return iter(self._events)

        def get_final_message(self):
            return self._final_message

    mock_client = MagicMock()
    mock_client.messages = MagicMock()

    events = [
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="thinking_delta", thinking="Thought."),
        ),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="text_delta", text="Answer."),
        ),
    ]
    final_message = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    mock_client.messages.stream.return_value = MockStream(events, final_message)

    with patch("autobyteus.llm.api.claude_llm.ClaudeLLM.initialize", return_value=mock_client):
        llm = ClaudeLLM(
            model=_make_model(),
            llm_config=LLMConfig(extra_params={"thinking_enabled": True, "thinking_budget_tokens": 2048}),
        )

        contents = []
        reasonings = []

        async for chunk in llm._stream_user_message_to_llm(LLMUserMessage(content="hello")):
            if chunk.content:
                contents.append(chunk.content)
            if chunk.reasoning:
                reasonings.append(chunk.reasoning)

        assert "".join(contents) == "Answer."
        assert "".join(reasonings) == "Thought."
        assert llm.messages[-1].reasoning_content == "Thought."
