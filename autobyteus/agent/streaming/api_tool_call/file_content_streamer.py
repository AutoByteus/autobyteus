"""Content streamers for file tools in API tool call mode."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .json_string_field_extractor import JsonStringFieldExtractor


@dataclass
class FileContentStreamUpdate:
    """Incremental update from a file content streamer."""

    content_delta: str = ""
    path: Optional[str] = None
    content_complete: Optional[str] = None


class _BaseFileContentStreamer:
    def __init__(self, content_key: str):
        self._content_key = content_key
        self._extractor = JsonStringFieldExtractor(
            stream_fields={content_key},
            final_fields={"path", content_key},
        )
        self.path: Optional[str] = None
        self.content: Optional[str] = None

    def feed(self, json_delta: str) -> FileContentStreamUpdate:
        result = self._extractor.feed(json_delta)

        if "path" in result.completed and self.path is None:
            self.path = result.completed["path"]

        if self._content_key in result.completed:
            self.content = result.completed[self._content_key]

        return FileContentStreamUpdate(
            content_delta=result.deltas.get(self._content_key, ""),
            path=result.completed.get("path"),
            content_complete=result.completed.get(self._content_key),
        )


class WriteFileContentStreamer(_BaseFileContentStreamer):
    """Streams decoded write_file content from JSON argument deltas."""

    def __init__(self):
        super().__init__(content_key="content")


class PatchFileContentStreamer(_BaseFileContentStreamer):
    """Streams decoded patch_file content from JSON argument deltas."""

    def __init__(self):
        super().__init__(content_key="patch")
