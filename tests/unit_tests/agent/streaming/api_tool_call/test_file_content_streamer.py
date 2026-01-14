"""Tests for file content streamers used by API tool call streaming."""

from autobyteus.agent.streaming.api_tool_call.file_content_streamer import (
    WriteFileContentStreamer,
    PatchFileContentStreamer,
)


def test_write_file_streamer_emits_content_and_path():
    streamer = WriteFileContentStreamer()

    update1 = streamer.feed('{"path":"a.txt","content":"hi')
    assert update1.content_delta == "hi"
    assert update1.path == "a.txt"
    assert update1.content_complete is None

    update2 = streamer.feed('\\')
    assert update2.content_delta == ""

    update3 = streamer.feed('nthere"}')
    assert update3.content_delta == "\nthere"
    assert update3.content_complete == "hi\nthere"
    assert streamer.path == "a.txt"
    assert streamer.content == "hi\nthere"


def test_patch_file_streamer_emits_patch_content():
    streamer = PatchFileContentStreamer()

    update1 = streamer.feed('{"patch":"@@ -1 +1 @@')
    assert update1.content_delta == "@@ -1 +1 @@"

    update2 = streamer.feed('\\')
    assert update2.content_delta == ""

    update3 = streamer.feed('n-foo\\n+bar"}')
    assert update3.content_delta == "\n-foo\n+bar"
    assert update3.content_complete == "@@ -1 +1 @@\n-foo\n+bar"


def test_streamer_handles_content_before_path():
    streamer = WriteFileContentStreamer()

    update1 = streamer.feed('{"content":"h')
    assert update1.content_delta == "h"
    assert update1.content_complete is None

    update2 = streamer.feed('i","path":"later.txt"}')
    assert update2.content_delta == "i"
    assert update2.content_complete == "hi"
    assert update2.path == "later.txt"
    assert streamer.path == "later.txt"
