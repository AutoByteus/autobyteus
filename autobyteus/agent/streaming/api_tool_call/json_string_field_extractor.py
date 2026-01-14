"""
Incremental JSON string field extractor for API tool call argument deltas.

This parser is intentionally small and focused: it streams specific string
fields (e.g., path/content/patch) from a JSON object as deltas arrive.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional


@dataclass
class FieldExtractionResult:
    """Holds incremental deltas and completed values for extracted fields."""

    deltas: Dict[str, str] = field(default_factory=dict)
    completed: Dict[str, str] = field(default_factory=dict)


class JsonStringFieldExtractor:
    """
    Incrementally extracts specified string fields from a JSON object.

    The extractor consumes raw JSON fragments and yields decoded string deltas
    for configured fields. It is resilient to chunk boundaries and handles
    common JSON escapes.
    """

    def __init__(
        self,
        stream_fields: Iterable[str],
        final_fields: Optional[Iterable[str]] = None,
    ):
        self._stream_fields = set(stream_fields)
        self._final_fields = set(final_fields) if final_fields is not None else set(stream_fields)
        self._targets = self._stream_fields | self._final_fields
        self._mode = "scan"
        self._escape = False
        self._unicode_escape: Optional[str] = None
        self._current_key: Optional[str] = None
        self._current_value_key: Optional[str] = None
        self._string_buffer: str = ""
        self._values: Dict[str, str] = {}
        self._pending_delta: Dict[str, str] = {}

    def feed(self, chunk: str) -> FieldExtractionResult:
        """Process a chunk and return any new deltas or completed values."""
        if not chunk:
            return FieldExtractionResult()

        self._pending_delta = {}
        completed: Dict[str, str] = {}

        for char in chunk:
            self._step(char, completed)

        return FieldExtractionResult(deltas=self._pending_delta.copy(), completed=completed)

    def _step(self, char: str, completed: Dict[str, str]) -> None:
        if self._mode == "scan":
            if char == '"':
                self._string_buffer = ""
                self._mode = "key"
            return

        if self._mode == "key":
            if self._escape:
                self._string_buffer += self._decode_escape(char)
                return
            if char == "\\":
                self._escape = True
                return
            if char == '"':
                self._current_key = self._string_buffer
                self._string_buffer = ""
                self._mode = "post_key"
                return
            self._string_buffer += char
            return

        if self._mode == "post_key":
            if char.isspace():
                return
            if char == ":":
                self._mode = "post_colon"
                return
            # Unexpected token; reset
            self._reset_string_state()
            self._mode = "scan"
            return

        if self._mode == "post_colon":
            if char.isspace():
                return
            if char == '"':
                self._mode = "value"
                self._current_value_key = self._current_key
                self._string_buffer = ""
                return
            # Non-string value; ignore and reset
            self._current_key = None
            self._mode = "scan"
            return

        if self._mode == "value":
            if self._escape:
                decoded = self._decode_escape(char)
                self._append_value(decoded, completed)
                return
            if char == "\\":
                self._escape = True
                return
            if char == '"':
                self._finalize_value(completed)
                self._mode = "scan"
                return
            self._append_value(char, completed)

    def _append_value(self, decoded_char: str, completed: Dict[str, str]) -> None:
        key = self._current_value_key
        if not key:
            return
        if key in self._targets:
            if key in self._stream_fields:
                self._pending_delta[key] = self._pending_delta.get(key, "") + decoded_char
            self._values[key] = self._values.get(key, "") + decoded_char

    def _finalize_value(self, completed: Dict[str, str]) -> None:
        key = self._current_value_key
        if key in self._final_fields and key in self._values:
            completed[key] = self._values[key]
        self._current_key = None
        self._current_value_key = None
        self._string_buffer = ""
        self._escape = False
        self._unicode_escape = None

    def _reset_string_state(self) -> None:
        self._current_key = None
        self._current_value_key = None
        self._string_buffer = ""
        self._escape = False
        self._unicode_escape = None

    def _decode_escape(self, char: str) -> str:
        """Decode common JSON escapes, tracking state for unicode if needed."""
        if self._unicode_escape is not None:
            self._unicode_escape += char
            if len(self._unicode_escape) == 4:
                try:
                    decoded = chr(int(self._unicode_escape, 16))
                except ValueError:
                    decoded = ""
                self._unicode_escape = None
                self._escape = False
                return decoded
            return ""

        self._escape = False

        if char == "n":
            return "\n"
        if char == "t":
            return "\t"
        if char == "r":
            return "\r"
        if char == "\\":
            return "\\"
        if char == '"':
            return '"'
        if char == "u":
            self._unicode_escape = ""
            return ""
        return char
