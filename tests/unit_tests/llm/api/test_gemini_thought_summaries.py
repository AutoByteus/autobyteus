# file: autobyteus/tests/unit_tests/llm/api/test_gemini_thought_summaries.py
"""
Unit tests for Gemini thought summaries (include_thoughts).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autobyteus.llm.api.gemini_llm import GeminiLLM, _split_gemini_parts
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.user_message import LLMUserMessage


def _make_mock_client():
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()
    return client


def _make_model():
    return LLMModel(
        name="gemini-test",
        value="gemini-test-v1",
        provider=LLMProvider.GEMINI,
        llm_class=GeminiLLM,
        canonical_name="gemini-test",
    )


def test_split_gemini_parts_separates_thoughts():
    parts = [
        SimpleNamespace(text="Reasoning A", thought=True),
        SimpleNamespace(text="Content B", thought=False),
        SimpleNamespace(text="Reasoning C", thought=True),
    ]

    content, reasoning = _split_gemini_parts(parts)

    assert content == "Content B"
    assert reasoning == "Reasoning AReasoning C"


def test_generation_config_includes_thoughts_flag():
    client = _make_mock_client()
    runtime_info = SimpleNamespace(runtime="api")

    with patch("autobyteus.llm.api.gemini_llm.initialize_gemini_client_with_runtime", return_value=(client, runtime_info)):
        config = LLMConfig(extra_params={"thinking_level": "low", "include_thoughts": True})
        llm = GeminiLLM(model=_make_model(), llm_config=config)

        generation_config = llm._get_generation_config()
        assert generation_config.thinking_config.include_thoughts is True


@pytest.mark.asyncio
async def test_send_user_message_returns_reasoning_summary():
    client = _make_mock_client()
    runtime_info = SimpleNamespace(runtime="api")

    response = SimpleNamespace(
        text="fallback",
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(text="Thought summary.", thought=True),
                        SimpleNamespace(text="Final answer.", thought=False),
                    ]
                )
            )
        ],
    )

    client.aio.models.generate_content = AsyncMock(return_value=response)

    with patch("autobyteus.llm.api.gemini_llm.initialize_gemini_client_with_runtime", return_value=(client, runtime_info)):
        llm = GeminiLLM(
            model=_make_model(),
            llm_config=LLMConfig(extra_params={"thinking_level": "low", "include_thoughts": True})
        )

        result = await llm._send_user_message_to_llm(LLMUserMessage(content="hello"))

        assert result.content == "Final answer."
        assert result.reasoning == "Thought summary."


@pytest.mark.asyncio
async def test_stream_user_message_emits_reasoning_chunks():
    client = _make_mock_client()
    runtime_info = SimpleNamespace(runtime="api")

    async def mock_stream():
        yield SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(text="Thought.", thought=True),
                            SimpleNamespace(text="Answer.", thought=False),
                        ]
                    )
                )
            ]
        )

    client.aio.models.generate_content_stream = AsyncMock(return_value=mock_stream())

    with patch("autobyteus.llm.api.gemini_llm.initialize_gemini_client_with_runtime", return_value=(client, runtime_info)):
        llm = GeminiLLM(
            model=_make_model(),
            llm_config=LLMConfig(extra_params={"thinking_level": "low", "include_thoughts": True})
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
