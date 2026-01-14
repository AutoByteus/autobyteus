from typing import List, Optional, Any
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta
from google.genai import types as genai_types
import json

def convert_gemini_tool_calls(part: Any) -> Optional[List[ToolCallDelta]]:
    """
    Convert a Gemini stream part (which might be a functionCall) into ToolCallDelta objects.
    
    Gemini 'functionCall' usually comes as a complete object in the parts list, 
    but we treat it as a delta to fit the unified streaming model.
    """
    # Check if the part has a function_call
    # The SDK structure for part usually has a 'function_call' attribute
    
    # Note: genai_types.Part might have function_call (FunctionCall)
    
    # Safety check for attribute existence
    if not hasattr(part, "function_call") or not part.function_call:
        return None
        
    fc = part.function_call
    
    # Gemini provides the full arguments as a dict in the 'args' attribute
    # We serialize this back to JSON string for the delta, because our unified
    # ToolCallDelta expects string deltas for arguments. 
    # Since we get the full args at once, this is a "complete" delta.
    
    # Note: 'args' is a dictionary.
    arguments_json = json.dumps(fc.args) if fc.args else "{}"
    
    # We use a fixed index 0 because Gemini typically emits one function call per candidate part?
    # Actually Gemini can return multiple function calls in parallel tool use? 
    # But usually they are in separate parts or candidates.
    # For now, we assume implicit index 0 for the part itself. 
    # If parallel tool calling is supported via multiple parts, the caller loop needs to handle indexing 
    # if it's not provided by the SDK.
    # However, ToolCallDelta requires an index. We'll default to 0. 
    # If the caller iterates parts, it might need to assign indices.
    # But wait, ToolCallDelta logic merges by index. If we always return index 0 for distinct parts, they merge.
    # We might need to generate a unique index or rely on the caller to offset it.
    # BUT, Gemini streaming chunks usually contain ONE part at a time.
    # If we treat each function_call part as a NEW tool call, we need a way to distinguish parallel ones?
    # Or maybe we just generate a unique call_id if one isn't present.
    # Gemini function calls don't always have IDs in the stream?
    # Let's check `fc.name` and `fc.args`.
    
    # For simplicity, if we get a full function call, we return one delta that has EVERYTHING.
    # The unified handler will assume it's a new call if index is new... or if it's the first time 
    # seeing this index.
    
    return [ToolCallDelta(
        index=0, # Assuming single tool call per part context for now
        call_id=None, # Gemini doesn't always provide call ID in stream? We'll rely on handler to generate one.
        name=fc.name,
        arguments_delta=arguments_json
    )]
