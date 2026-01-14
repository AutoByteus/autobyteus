# file: autobyteus/autobyteus/llm/converters/openai_tool_call_converter.py
"""
Converter for OpenAI SDK tool call deltas to normalized ToolCallDelta format.
"""

from typing import List, Optional
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta

# Type checking import for OpenAI SDK types
try:
    from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
except ImportError:
    ChoiceDeltaToolCall = None  # type: ignore


def convert_openai_tool_calls(delta_tool_calls: Optional[List]) -> Optional[List[ToolCallDelta]]:
    """
    Convert OpenAI SDK tool call deltas to normalized ToolCallDelta objects.

    Args:
        delta_tool_calls: List of ChoiceDeltaToolCall from OpenAI SDK, or None.

    Returns:
        List of normalized ToolCallDelta objects, or None if input is None/empty.
    """
    if not delta_tool_calls:
        return None

    result = []
    for tc in delta_tool_calls:
        # Extract fields from OpenAI's ChoiceDeltaToolCall
        result.append(ToolCallDelta(
            index=tc.index,
            call_id=tc.id if tc.id else None,
            name=tc.function.name if tc.function and tc.function.name else None,
            arguments_delta=tc.function.arguments if tc.function and tc.function.arguments else None,
        ))
    return result
