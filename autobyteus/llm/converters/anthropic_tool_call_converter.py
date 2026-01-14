from typing import List, Optional, Any
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta

# Anthropic event types are typically simple objects or dicts from the SDK stream
# The SDK yields `MessageStreamEvent` objects.

def convert_anthropic_tool_call(event: Any) -> Optional[List[ToolCallDelta]]:
    """
    Convert an Anthropic stream event into ToolCallDelta objects.
    
    Handles:
    - ContentBlockStartEvent (type='content_block_start') -> Tool Name + ID
    - ContentBlockDeltaEvent (type='content_block_delta') -> Arguments Delta
    """
    
    # Handle ContentBlockStartEvent (Start of tool use)
    # event.content_block.type == 'tool_use'
    if event.type == "content_block_start":
        if event.content_block.type == "tool_use":
            return [ToolCallDelta(
                index=event.index, # Anthropic provides index
                call_id=event.content_block.id,
                name=event.content_block.name,
                arguments_delta=None # No args yet
            )]
            
    # Handle ContentBlockDeltaEvent (JSON args update)
    elif event.type == "content_block_delta":
        if event.delta.type == "input_json_delta":
            return [ToolCallDelta(
                index=event.index, # Anthropic provides index matching the start event
                call_id=None,
                name=None,
                arguments_delta=event.delta.partial_json
            )]

    return None
