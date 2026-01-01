"""
Unit tests for the streaming parser events module.
"""
import pytest
from autobyteus.agent.streaming.parser.events import (
    PartStartEvent,
    PartDeltaEvent,
    PartEndEvent,
    TextPart,
    ToolCallPart,
    ReasoningPart,
)


class TestMessageParts:
    """Tests for MessagePart models."""

    def test_text_part(self):
        part = TextPart(id="1", content="hello")
        assert part.type == "text"
        assert part.content == "hello"

    def test_tool_call_part(self):
        part = ToolCallPart(
            id="2",
            tool_name="test_tool",
            arguments={"arg": 1},
            raw_arguments='{"arg": 1}'
        )
        assert part.type == "tool_call"
        assert part.tool_name == "test_tool"

    def test_reasoning_part(self):
        part = ReasoningPart(id="3", content="thinking")
        assert part.type == "reasoning"
        assert part.content == "thinking"


class TestPartEvents:
    """Tests for PartEvent classes."""

    def test_part_start_event(self):
        event = PartStartEvent(
            part_id="p1",
            part_type="tool_call",
            metadata={"tool_name": "calc"}
        )
        assert event.event == "part_start"
        assert event.part_id == "p1"
        assert event.part_type == "tool_call"
        assert event.metadata["tool_name"] == "calc"
        
        d = event.model_dump()
        assert d["event"] == "part_start"
        assert d["part_id"] == "p1"
        assert d["part_type"] == "tool_call"
        assert d["metadata"] == {"tool_name": "calc"}

    def test_part_delta_event(self):
        event = PartDeltaEvent(
            part_id="p1",
            delta="hello"
        )
        assert event.event == "part_delta"
        assert event.part_id == "p1"
        assert event.delta == "hello"
        
        d = event.model_dump()
        assert d["event"] == "part_delta"
        assert d["part_id"] == "p1"
        assert d["delta"] == "hello"

    def test_part_end_event(self):
        event = PartEndEvent(
            part_id="p1",
            metadata={"status": "done"}
        )
        assert event.event == "part_end"
        assert event.part_id == "p1"
        assert event.metadata == {"status": "done"}
        
        d = event.model_dump()
        assert d["event"] == "part_end"
        assert d["part_id"] == "p1"
        assert d["metadata"] == {"status": "done"}

