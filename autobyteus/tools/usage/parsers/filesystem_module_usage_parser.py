from __future__ import annotations

import json
import logging
import re
from typing import List

from .base_parser import BaseToolUsageParser
from .exceptions import ToolUsageParseException
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)


class FilesystemModuleUsageParser(BaseToolUsageParser):
    """Parses `[RUN_MODULE] ... [/RUN_MODULE]` blocks containing JSON payloads."""

    BLOCK_PATTERN = re.compile(r"\[RUN_MODULE\](.*?)\[/RUN_MODULE\]", re.DOTALL | re.IGNORECASE)

    def get_name(self) -> str:
        return "filesystem_module_usage_parser"

    def parse(self, response: CompleteResponse) -> List[ToolInvocation]:  # type: ignore[override]
        text = response.content
        if not text:
            return []
        invocations: List[ToolInvocation] = []
        for match in self.BLOCK_PATTERN.finditer(text):
            block = match.group(1).strip()
            if not block:
                continue
            try:
                payload = json.loads(block)
            except json.JSONDecodeError as exc:
                logger.warning("Failed to parse module block as JSON: %s", exc)
                raise ToolUsageParseException("Invalid JSON inside RUN_MODULE block", original_exception=exc)

            name = payload.get("name") or payload.get("module")
            args = payload.get("args") or payload.get("arguments") or {}
            if not name:
                logger.warning("RUN_MODULE block missing 'name': %s", block[:100])
                continue
            if not isinstance(args, dict):
                logger.warning("RUN_MODULE block arguments must be an object. Got %s", type(args))
                raise ToolUsageParseException("RUN_MODULE arguments must be an object")

            invocations.append(ToolInvocation(name=name, arguments=args))

        return invocations
