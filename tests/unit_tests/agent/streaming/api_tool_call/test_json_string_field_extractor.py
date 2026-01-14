"""Tests for JsonStringFieldExtractor."""

from autobyteus.agent.streaming.api_tool_call.json_string_field_extractor import (
    JsonStringFieldExtractor,
)


def test_extracts_path_and_content_across_chunks():
    extractor = JsonStringFieldExtractor(stream_fields={"content"}, final_fields={"path", "content"})

    res1 = extractor.feed('{"path":"a.txt","content":"hel')
    assert res1.completed == {"path": "a.txt"}
    assert res1.deltas == {"content": "hel"}

    res2 = extractor.feed('lo\\')
    assert res2.deltas == {"content": "lo"}
    assert res2.completed == {}

    res3 = extractor.feed('nwo')
    assert res3.deltas == {"content": "\nwo"}
    assert res3.completed == {}

    res4 = extractor.feed('rld"}')
    assert res4.deltas == {"content": "rld"}
    assert res4.completed == {"content": "hello\nworld"}


def test_handles_escaped_quotes_and_backslashes():
    extractor = JsonStringFieldExtractor(stream_fields={"content"})

    res1 = extractor.feed('{"content":"He said: \\')
    assert res1.deltas == {"content": "He said: "}

    res2 = extractor.feed('"hi\\')
    assert res2.deltas == {"content": '"hi'}

    res3 = extractor.feed('" and \\\\\\\\ ok"}')
    assert res3.deltas == {"content": '" and \\\\ ok'}
    assert res3.completed == {"content": 'He said: "hi" and \\\\ ok'}
