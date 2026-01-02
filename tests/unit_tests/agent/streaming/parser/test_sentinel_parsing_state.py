"""
Unit tests for sentinel-based parsing.
"""
from autobyteus.agent.streaming.parser.parser_context import ParserConfig
from autobyteus.agent.streaming.parser.streaming_parser import StreamingParser, extract_segments


def test_sentinel_file_segment():
    config = ParserConfig(strategy_order=["sentinel"])
    parser = StreamingParser(config)

    text = (
        '[[SEG_START {"type":"file","path":"/a.py"}]]'
        'print("hi")'
        '[[SEG_END]]'
    )
    events = parser.feed_and_finalize(text)
    segments = extract_segments(events)

    file_segments = [s for s in segments if s["type"] == "file"]
    assert len(file_segments) == 1
    assert file_segments[0]["metadata"].get("path") == "/a.py"
    assert file_segments[0]["content"] == 'print("hi")'


def test_sentinel_header_split_across_chunks():
    config = ParserConfig(strategy_order=["sentinel"])
    parser = StreamingParser(config)

    chunks = [
        '[[SEG_START {"type":"bash","path":"/x"',
        '}]]echo hi[[SEG_END]]'
    ]
    events = []
    for chunk in chunks:
        events.extend(parser.feed(chunk))
    events.extend(parser.finalize())

    segments = extract_segments(events)
    bash_segments = [s for s in segments if s["type"] == "bash"]
    assert len(bash_segments) == 1
    assert bash_segments[0]["content"] == "echo hi"


def test_sentinel_invalid_header_falls_back_to_text():
    config = ParserConfig(strategy_order=["sentinel"])
    parser = StreamingParser(config)

    text = '[[SEG_START not-json]]oops[[SEG_END]]'
    events = parser.feed_and_finalize(text)
    segments = extract_segments(events)

    text_segments = [s for s in segments if s["type"] == "text"]
    assert len(text_segments) >= 1
    assert "SEG_START" in text_segments[0]["content"]
