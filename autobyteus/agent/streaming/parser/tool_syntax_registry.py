"""
Registry for mapping segment syntaxes to tool invocations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from .events import SegmentType

ToolArgsBuilder = Callable[[dict, str], Optional[dict]]


@dataclass(frozen=True)
class ToolSyntaxSpec:
    """Defines how a segment type maps to a tool invocation."""

    tool_name: str
    build_arguments: ToolArgsBuilder


def _build_write_file_args(metadata: dict, content: str) -> Optional[dict]:
    path = metadata.get("path")
    if not path:
        return None
    return {"path": path, "content": content}


def _build_run_bash_args(metadata: dict, content: str) -> Optional[dict]:
    command = content or metadata.get("cmd") or ""
    if not command:
        return None
    return {"command": command}


def _build_patch_file_args(metadata: dict, content: str) -> Optional[dict]:
    path = metadata.get("path")
    if not path:
        return None
    # 'content' here is the accumulated patch delta from the stream
    return {"path": path, "patch": content}


_TOOL_SYNTAX_REGISTRY: Dict[SegmentType, ToolSyntaxSpec] = {
    SegmentType.WRITE_FILE: ToolSyntaxSpec(
        tool_name="write_file",
        build_arguments=_build_write_file_args,
    ),
    SegmentType.RUN_BASH: ToolSyntaxSpec(
        tool_name="run_bash",
        build_arguments=_build_run_bash_args,
    ),
    SegmentType.PATCH_FILE: ToolSyntaxSpec(
        tool_name="patch_file",
        build_arguments=_build_patch_file_args,
    ),
}


def get_tool_syntax_spec(segment_type: SegmentType) -> Optional[ToolSyntaxSpec]:
    """Return tool syntax spec for a segment type if registered."""
    return _TOOL_SYNTAX_REGISTRY.get(segment_type)


def tool_syntax_registry_items() -> Tuple[Tuple[SegmentType, ToolSyntaxSpec], ...]:
    """Expose registry items for inspection/testing."""
    return tuple(_TOOL_SYNTAX_REGISTRY.items())
