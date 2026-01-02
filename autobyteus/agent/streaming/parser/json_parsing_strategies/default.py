"""Default JSON tool-call parsing for generic formats."""
from typing import Any, List
import json

from .base import ToolCallData, coerce_arguments


class DefaultJsonToolParsingStrategy:
    """Parses the default Autobyteus JSON tool call format."""

    def parse(self, raw_json: str) -> List[ToolCallData]:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return []

        tool = None
        if isinstance(data, dict):
            tool = data.get("tool")
        if not isinstance(tool, dict):
            return []

        name = tool.get("function")
        if isinstance(name, dict):
            name = name.get("name")
        if not isinstance(name, str) or not name:
            return []

        args = tool.get("parameters")
        if args is None:
            args = tool.get("arguments")
        arguments = coerce_arguments(args)

        return [{"name": name, "arguments": arguments}]
