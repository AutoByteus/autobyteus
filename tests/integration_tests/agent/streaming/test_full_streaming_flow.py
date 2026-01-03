"""
Integration tests for the complete streaming response flow.

Tests the full pipeline: StreamingResponseHandler → StreamingParser → ToolInvocationAdapter
"""
import pytest
from autobyteus.agent.streaming import (
    StreamingResponseHandler,
    SegmentType,
    SegmentEventType,
)


class TestFullStreamingFlow:
    """End-to-end tests for the streaming response pipeline."""

    def test_complete_llm_response_with_tools(self):
        """
        Simulates a complete LLM response with text and tool calls.
        Verifies events are emitted and invocations are created correctly.
        """
        collected_events = []
        collected_invocations = []
        
        handler = StreamingResponseHandler(
            on_segment_event=lambda e: collected_events.append(e),
            on_tool_invocation=lambda inv: collected_invocations.append(inv)
        )
        
        # Simulate chunked LLM response
        chunks = [
            "I'll read the file for you.\n\n",
            '<tool name="read_file">',
            "<path>/src/main.py</path>",
            "</tool>",
            "\n\nHere's what I found."
        ]
        
        for chunk in chunks:
            handler.feed(chunk)
        
        handler.finalize()
        
        # Verify events were collected via callback
        assert len(collected_events) > 0
        
        # Verify invocation was created
        assert len(collected_invocations) == 1
        inv = collected_invocations[0]
        assert inv.name == "read_file"
        assert inv.arguments == {"path": "/src/main.py"}
        
        # Verify segment_id == invocation id
        tool_starts = [e for e in collected_events if e.segment_type == SegmentType.TOOL_CALL]
        assert len(tool_starts) == 1
        assert tool_starts[0].segment_id == inv.id

    def test_multiple_tool_calls_in_sequence(self):
        """Multiple tool calls get unique IDs."""
        handler = StreamingResponseHandler()
        
        response = '''
First I'll read file A:
<tool name="read_file"><path>/a.py</path></tool>

Now I'll read file B:
<tool name="read_file"><path>/b.py</path></tool>

Done!
'''
        handler.feed(response)
        handler.finalize()
        
        invocations = handler.get_all_invocations()
        
        assert len(invocations) == 2
        assert invocations[0].arguments["path"] == "/a.py"
        assert invocations[1].arguments["path"] == "/b.py"
        # IDs should be different
        assert invocations[0].id != invocations[1].id

    def test_segment_id_is_stable_for_approval_flow(self):
        """
        Critical test: segment_id from parsing must be the invocation ID
        that frontend uses for approval. This enables the round-trip:
        
        Backend parses → emits segment_id
        Frontend renders with segment_id as invocationId
        User approves → sends invocationId back
        Backend finds tool by invocationId
        """
        events_by_id = {}
        
        def track_event(event):
            if event.segment_id not in events_by_id:
                events_by_id[event.segment_id] = []
            events_by_id[event.segment_id].append(event)
        
        handler = StreamingResponseHandler(on_segment_event=track_event)
        
        handler.feed('<tool name="write_file"><path>/out.txt</path><content>Hello</content></tool>')
        handler.finalize()
        
        inv = handler.get_all_invocations()[0]
        
        # The invocation ID must exist in our tracked events
        assert inv.id in events_by_id
        
        # Should have START, CONTENT, END events for this segment
        segment_events = events_by_id[inv.id]
        event_types = [e.event_type for e in segment_events]
        assert SegmentEventType.START in event_types
        assert SegmentEventType.END in event_types

    def test_mixed_content_types(self):
        """Response with text, file, bash, and tool segments."""
        handler = StreamingResponseHandler()
        
        response = '''
Let me help you:

<file path="/output.py">
def hello():
    print("hello")
</file>

<bash>
python output.py
</bash>

<tool name="verify_result"><expected>hello</expected></tool>

All done!
'''
        handler.feed(response)
        handler.finalize()
        
        events = handler.get_all_events()
        invocations = handler.get_all_invocations()
        
        # Count segment types
        segment_types = [e.segment_type for e in events if e.segment_type]
        
        assert SegmentType.TEXT in segment_types
        assert SegmentType.FILE in segment_types
        assert SegmentType.BASH in segment_types
        assert SegmentType.TOOL_CALL in segment_types
        
        # File, bash, and tool create invocations
        assert len(invocations) == 3
        names = [inv.name for inv in invocations]
        assert "write_file" in names
        assert "run_terminal_cmd" in names
        assert "verify_result" in names

    def test_write_file_file_segment_with_raw_html_comment(self):
        """File shorthand supports raw HTML (including comments) without escaping."""
        handler = StreamingResponseHandler()

        response = """<file path="/site/index.html">
<!doctype html>
<html>
  <body>
    <!-- hero -->
    <div class="hero">& welcome</div>
  </body>
</html>
</file>"""
        handler.feed(response)
        handler.finalize()

        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        assert invocations[0].name == "write_file"
        assert invocations[0].arguments["path"] == "/site/index.html"
        content = invocations[0].arguments["content"]
        assert "<!-- hero -->" in content
        assert "<div class=\"hero\">& welcome</div>" in content

    def test_write_file_tool_with_cdata_content(self):
        """XML tool calls can use CDATA for raw content without entity escaping."""
        handler = StreamingResponseHandler()

        response = (
            "<tool name=\"write_file\">"
            "<path>/site/app.js</path>"
            "<content><![CDATA["
            "const html = '<div class=\"app\">& ready</div>';\n"
            "// ok\n"
            "]]></content>"
            "</tool>"
        )
        handler.feed(response)
        handler.finalize()

        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        assert invocations[0].name == "write_file"
        assert invocations[0].arguments["path"] == "/site/app.js"
        content = invocations[0].arguments["content"]
        assert "<div class=\"app\">& ready</div>" in content
        assert "// ok" in content

    def test_tool_call_full_chunk_with_unescaped_lt(self):
        """Single-chunk tool call handles unescaped '<' in arg text."""
        handler = StreamingResponseHandler()

        response = (
            "<tool name=\"create_tasks\">"
            "<arguments>"
            "<arg name=\"tasks\">"
            "<item>"
            "<arg name=\"task_name\">implement_fibonacci</arg>"
            "<arg name=\"description\">Handle n <= 0 case</arg>"
            "</item>"
            "</arg>"
            "</arguments>"
            "</tool>"
        )
        handler.feed(response)
        handler.finalize()

        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        inv = invocations[0]
        assert inv.name == "create_tasks"
        tasks = inv.arguments.get("tasks")
        assert tasks == [{"task_name": "implement_fibonacci", "description": "Handle n <= 0 case"}]


class TestStreamingChunkedInput:
    """Tests for realistic chunked input scenarios."""

    def test_tool_tag_split_across_chunks(self):
        """Tool tag arriving in multiple chunks."""
        handler = StreamingResponseHandler()
        
        handler.feed('<tool name="te')
        handler.feed('st"><arg>val')
        handler.feed('ue</arg></to')
        handler.feed('ol>')
        handler.finalize()
        
        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        assert invocations[0].name == "test"
        assert invocations[0].arguments == {"arg": "value"}

    def test_single_character_chunks(self):
        """Extreme case: each character as separate chunk."""
        handler = StreamingResponseHandler()
        
        content = '<tool name="x"><a>1</a></tool>'
        for char in content:
            handler.feed(char)
        handler.finalize()
        
        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        assert invocations[0].name == "x"

    def test_tool_call_chunked_with_unescaped_lt(self):
        """Chunked tool call handles unescaped '<' in arg text."""
        handler = StreamingResponseHandler()

        chunks = [
            "<tool name=\"create_tasks\"><arguments><arg name=\"tasks\"><item>"
            "<arg name=\"description\">Handle n <",
            "= 0 case</arg></item></arg></arguments></tool>",
        ]
        for chunk in chunks:
            handler.feed(chunk)
        handler.finalize()

        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        inv = invocations[0]
        tasks = inv.arguments.get("tasks")
        assert tasks == [{"description": "Handle n <= 0 case"}]

    def test_sentinel_tool_call_full_chunk_with_unescaped_lt(self):
        """Sentinel tool call works with a single complete chunk."""
        handler = StreamingResponseHandler(parser_name="sentinel")

        response = (
            '[[SEG_START {"type":"tool","tool_name":"create_tasks","arguments":'
            '{"tasks":[{"task_name":"implement_fibonacci","description":"Handle n <= 0 case"}]}}]]'
            '[[SEG_END]]'
        )
        handler.feed(response)
        handler.finalize()

        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        inv = invocations[0]
        assert inv.name == "create_tasks"
        tasks = inv.arguments.get("tasks")
        assert tasks == [{"task_name": "implement_fibonacci", "description": "Handle n <= 0 case"}]

    def test_sentinel_tool_call_chunked_with_unescaped_lt(self):
        """Sentinel tool call works when chunked across markers."""
        handler = StreamingResponseHandler(parser_name="sentinel")

        chunks = [
            '[[SEG_START {"type":"tool","tool_name":"create_tasks","arguments":',
            '{"tasks":[{"description":"Handle n <',
            '= 0 case"}]}}]]',
            '[[SEG_END]]',
        ]
        for chunk in chunks:
            handler.feed(chunk)
        handler.finalize()

        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        tasks = invocations[0].arguments.get("tasks")
        assert tasks == [{"description": "Handle n <= 0 case"}]
