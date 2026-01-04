"""
Utility parsers for tool call argument extraction.

These functions are intentionally decoupled from streaming states so the
ToolInvocationAdapter can be the single source of truth for arguments.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

from .json_parsing_strategies.base import JsonToolParsingStrategy

_ARGS_OPEN = "<arguments>"
_ARGS_CLOSE = "</arguments>"
_TAG_SPLIT_PATTERN = re.compile(r"(<[A-Za-z!/][^>]*>)")
_ENTITY_PATTERN = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")


def parse_xml_arguments(content: str) -> Dict[str, Any]:
    """
    Parse XML tool arguments from a tool-call content body.

    Supports:
    1) <arguments><arg name="x">...</arg></arguments>
    2) <arguments><path>...</path></arguments>
    3) Direct content without <arguments> wrapper
    """
    args_match = re.search(
        rf"{_ARGS_OPEN}(.*?){_ARGS_CLOSE}",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    if args_match:
        args_content = args_match.group(1)
    else:
        args_content = content.strip()

    if not args_content:
        return {}

    try:
        root = ET.fromstring(f"<root>{args_content}</root>")
        return _parse_xml_children(root)
    except ET.ParseError:
        sanitized = _sanitize_xml_fragment(args_content)
        try:
            root = ET.fromstring(f"<root>{sanitized}</root>")
            return _parse_xml_children(root)
        except ET.ParseError:
            return _parse_legacy_arguments(args_content)


def parse_json_tool_call(
    json_str: str,
    parser: Optional[JsonToolParsingStrategy] = None,
) -> Optional[Dict[str, Any]]:
    """
    Parse a JSON string into tool call info.

    Returns dict with 'name' and 'arguments', or None if invalid.
    """
    if parser is not None:
        parsed_calls = parser.parse(json_str)
        if parsed_calls:
            return parsed_calls[0]
        return None

    try:
        data = json.loads(json_str)

        if isinstance(data, list) and data:
            data = data[0]

        if isinstance(data, dict):
            name = (
                data.get("name")
                or data.get("tool")
                or data.get("function", {}).get("name")
                or "unknown"
            )
            arguments = (
                data.get("arguments")
                or data.get("parameters")
                or data.get("function", {}).get("arguments")
                or {}
            )
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    pass
            return {"name": name, "arguments": arguments}
    except json.JSONDecodeError:
        return None

    return None


def _parse_xml_children(element: ET.Element) -> Dict[str, Any]:
    arguments: Dict[str, Any] = {}
    for child in element:
        name = child.attrib.get("name") or child.tag
        if not name:
            continue
        arguments[name] = _parse_xml_value(child)
    return arguments


def _parse_xml_value(element: ET.Element) -> Any:
    items = [child for child in element if child.tag == "item"]
    if items:
        return [_parse_item_value(item) for item in items]

    arg_children = [child for child in element if child.tag == "arg"]
    if arg_children:
        return _parse_xml_children(element)

    other_children = [child for child in element if child.tag not in {"arg", "item"}]
    if other_children:
        return _parse_xml_children(element)

    text = element.text or ""
    return text.strip()


def _parse_item_value(element: ET.Element) -> Any:
    arg_children = [child for child in element if child.tag == "arg"]
    if arg_children:
        return _parse_xml_children(element)
    other_children = [child for child in element if child.tag not in {"arg", "item"}]
    if other_children:
        return _parse_xml_children(element)
    text = element.text or ""
    return text.strip()


def _parse_legacy_arguments(args_content: str) -> Dict[str, Any]:
    arguments: Dict[str, Any] = {}
    arg_pattern = re.compile(r"<(\\w+)>(.*?)</\\1>", re.DOTALL)
    for match in arg_pattern.finditer(args_content):
        arg_name = match.group(1)
        arg_value = match.group(2).strip()
        arguments[arg_name] = arg_value
    return arguments


def _sanitize_xml_fragment(fragment: str) -> str:
    """Escape raw text to make fragment XML-safe without touching tags."""
    parts = _TAG_SPLIT_PATTERN.split(fragment)
    sanitized_parts = []
    for part in parts:
        if not part:
            continue
        if part.startswith("<") and part.endswith(">"):
            sanitized_parts.append(part)
            continue
        escaped = _ENTITY_PATTERN.sub("&amp;", part)
        escaped = escaped.replace("<", "&lt;")
        sanitized_parts.append(escaped)
    return "".join(sanitized_parts)
