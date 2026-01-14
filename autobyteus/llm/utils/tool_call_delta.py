# file: autobyteus/autobyteus/llm/utils/tool_call_delta.py
"""
Provider-agnostic representation of streaming tool call updates.

This dataclass normalizes tool call deltas from different LLM providers
(OpenAI, Anthropic, Gemini) into a common format for the streaming architecture.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolCallDelta:
    """
    A normalized, provider-agnostic representation of a tool call update
    received during streaming.

    Attributes:
        index: Position in parallel tool calls (0-based). Used to track
               multiple concurrent tool calls in the same response.
        call_id: Unique ID for this tool call. Present only in the first
                 chunk for this index.
        name: Tool/function name. Present only in the first chunk for this index.
        arguments_delta: Partial JSON string of arguments. Accumulated across
                         multiple chunks to form complete arguments.
    """
    index: int
    call_id: Optional[str] = None
    name: Optional[str] = None
    arguments_delta: Optional[str] = None
