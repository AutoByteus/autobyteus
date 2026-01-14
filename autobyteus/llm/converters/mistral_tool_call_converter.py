from typing import List, Optional, Any
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta
import logging

logger = logging.getLogger(__name__)

def convert_mistral_tool_calls(tool_calls: List[Any]) -> Optional[List[ToolCallDelta]]:
    """
    Convert Mistral streaming tool calls (similar to OpenAI) into ToolCallDelta objects.
    """
    if not tool_calls:
        return None

    deltas = []
    for tool_call in tool_calls:
        # Mistral SDK 'ToolCall' or dict in delta
        # Usually has: index, id, function (name, arguments)
        
        index = tool_call.get('index', 0) if isinstance(tool_call, dict) else getattr(tool_call, 'index', 0)
        call_id = tool_call.get('id', None) if isinstance(tool_call, dict) else getattr(tool_call, 'id', None)
        
        function = tool_call.get('function', None) if isinstance(tool_call, dict) else getattr(tool_call, 'function', None)
        name = None
        arguments = None
        
        if function:
            name = function.get('name', None) if isinstance(function, dict) else getattr(function, 'name', None)
            arguments = function.get('arguments', None) if isinstance(function, dict) else getattr(function, 'arguments', None)

        deltas.append(ToolCallDelta(
            index=index,
            call_id=call_id,
            name=name,
            arguments_delta=arguments
        ))

    return deltas
