# file: autobyteus/autobyteus/tools/usage/parsers/_string_decoders.py
"""Utility helpers for normalizing string content inside parsed tool payloads."""

from __future__ import annotations

import html
from typing import Any


def decode_html_entities(data: Any) -> Any:
    """Recursively decode HTML/XML entities in strings within a data structure."""
    if isinstance(data, dict):
        return {key: decode_html_entities(value) for key, value in data.items()}
    if isinstance(data, list):
        return [decode_html_entities(item) for item in data]
    if isinstance(data, str):
        return html.unescape(data)
    return data
