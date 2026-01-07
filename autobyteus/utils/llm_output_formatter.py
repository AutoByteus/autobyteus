from typing import Any, Dict, List
import dataclasses

def format_to_clean_string(data: Any, indent: int = 0) -> str:
    """
    Formats complex data structures into a clean, human-readable string optimized for LLM consumption.
    Avoids JSON syntax noise (braces, quotes) and YAML markers.
    Supports Dicts, Lists, Dataclasses, and Pydantic models.
    
    Args:
        data: The data to format.
        indent: Current indentation level (spaces).
        
    Returns:
        A formatted string representation of the data.
    """
    indent_str = " " * indent
    
    # Handle Dataclasses
    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        data = dataclasses.asdict(data)
    
    # Handle Pydantic Models (v1: dict(), v2: model_dump())
    elif hasattr(data, 'model_dump'):
        data = data.model_dump()
    elif hasattr(data, 'dict') and callable(getattr(data, 'dict')):
        # Fallback for Pydantic V1 or similar
        data = data.dict()

    if isinstance(data, dict):
        if not data:
            return f"{indent_str}(empty dict)"
        
        lines = []
        for key, value in data.items():
            value_str = format_to_clean_string(value, indent + 2)
            
            if isinstance(value, (dict, list)) and value:
                lines.append(f"{indent_str}{key}:\n{value_str}")
            elif dataclasses.is_dataclass(value) or hasattr(value, 'model_dump') or hasattr(value, 'dict'):
                 # Treat complex objects similarly to nested dicts
                 lines.append(f"{indent_str}{key}:\n{value_str}")
            else:
                lines.append(f"{indent_str}{key}: {value_str.lstrip()}")
        return "\n".join(lines)

    elif isinstance(data, list):
        if not data:
            return f"{indent_str}(empty list)"
        
        lines = []
        for item in data:
            item_str = format_to_clean_string(item, indent + 2)
            if isinstance(item, (dict, list)) or dataclasses.is_dataclass(item) or hasattr(item, 'model_dump'):
                 lines.append(f"{indent_str}- \n{item_str}")
            else:
                lines.append(f"{indent_str}- {item_str.lstrip()}")
        return "\n".join(lines)

    elif isinstance(data, str):
        lines = data.splitlines()
        if not lines:
            return f"{indent_str}\"\"" # Represent empty string explicitely or just empty? Let's use empty quotes for clarity if needed, or just nothing.
            # Actually, user wants clean text. Empty string usually implies no content.
            # Let's return "" if empty, but if it has content, indent it.
            return ""
        
        formatted_lines = [f"{indent_str}{line}" for line in lines]
        return "\n".join(formatted_lines)

    else:
        return f"{indent_str}{str(data)}"
