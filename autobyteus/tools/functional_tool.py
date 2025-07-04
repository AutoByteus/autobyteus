# file: autobyteus/autobyteus/tools/functional_tool.py
import inspect
import logging
import asyncio 
from typing import Callable, Optional, Any, Dict, Tuple, Union, get_origin, get_args, List as TypingList, TYPE_CHECKING, Type

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.registry import default_tool_registry, ToolDefinition
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class FunctionalTool(BaseTool):
    """
    An explicit wrapper class for functions decorated with @tool.
    This class holds the original function and all its derived metadata,
    and overrides BaseTool methods to provide this instance-specific information.
    """
    def __init__(self,
                 original_func: Callable,
                 name: str,
                 description: str,
                 argument_schema: ParameterSchema,
                 config_schema: Optional[ParameterSchema],
                 is_async: bool,
                 expects_context: bool,
                 expects_tool_state: bool,
                 func_param_names: TypingList[str],
                 instantiation_config: Optional[Dict[str, Any]] = None):
        super().__init__(config=ToolConfig(params=instantiation_config) if instantiation_config else None)
        self._original_func = original_func
        self._is_async = is_async
        self._expects_context = expects_context
        self._expects_tool_state = expects_tool_state
        self._func_param_names = func_param_names
        self._instantiation_config = instantiation_config or {}
        
        # This instance has its own state dictionary, inherited from BaseTool's __init__
        # self.tool_state: Dict[str, Any] = {} # This is now handled by super().__init__()
        
        # Override instance methods to provide specific schema info
        self.get_name = lambda: name
        self.get_description = lambda: description
        self.get_argument_schema = lambda: argument_schema
        self.get_config_schema = lambda: config_schema
        
        logger.debug(f"FunctionalTool instance created for function '{original_func.__name__}' registered as '{name}'.")

    @classmethod
    def get_name(cls) -> str:
        return "FunctionalTool"

    @classmethod
    def get_description(cls) -> str:
        return "A wrapper for a decorated function. Specifics are instance-based."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        return None

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> Any:
        call_args = {}
        for p_name in self._func_param_names:
            if p_name in kwargs:
                call_args[p_name] = kwargs[p_name]
        
        if self._expects_context:
            call_args['context'] = context
        
        if self._expects_tool_state:
            call_args['tool_state'] = self.tool_state
            
        if self._is_async:
            return await self._original_func(**call_args)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self._original_func(**call_args))

# --- Helper functions for the decorator ---

_TYPE_MAPPING = {
    int: ParameterType.INTEGER,
    float: ParameterType.FLOAT,
    bool: ParameterType.BOOLEAN,
    str: ParameterType.STRING,
    dict: ParameterType.OBJECT,
    list: ParameterType.ARRAY,
}

def _python_type_to_json_schema(py_type: Any) -> Optional[Dict[str, Any]]:
    if py_type is str: return {"type": "string"}
    if py_type is int: return {"type": "integer"}
    if py_type is float: return {"type": "number"}
    if py_type is bool: return {"type": "boolean"}
    if py_type is dict: return {"type": "object"}
    if py_type is list: return {"type": "array", "items": True} 
    
    origin_type = get_origin(py_type)
    if origin_type is Union:
        args = get_args(py_type)
        non_none_types = [t for t in args if t is not type(None)]
        if len(non_none_types) == 1: return _python_type_to_json_schema(non_none_types[0])
        return None
    if origin_type is TypingList or origin_type is list:
        list_args = get_args(py_type)
        if list_args and len(list_args) == 1:
            item_schema = _python_type_to_json_schema(list_args[0])
            return {"type": "array", "items": item_schema if item_schema else True}
        return {"type": "array", "items": True} 
    if origin_type is Dict or origin_type is dict: return {"type": "object"}
    logger.debug(f"Could not map Python type {py_type} to a simple JSON schema for array items.")
    return None

def _get_parameter_type_from_hint(py_type: Any, param_name: str) -> Tuple[ParameterType, Optional[Dict[str, Any]]]:
    origin_type = get_origin(py_type)
    actual_type = py_type
    array_item_js_schema: Optional[Dict[str, Any]] = None

    if origin_type is Union: 
        args = get_args(py_type)
        non_none_type_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_type_args) == 1: 
            actual_type = non_none_type_args[0]
            origin_type = get_origin(actual_type) 
        else:
            logger.warning(f"Complex Union type hint {py_type} for param '{param_name}' encountered. Defaulting to STRING.")
            return ParameterType.STRING, None 
    
    if actual_type is inspect.Parameter.empty: 
        logger.warning(f"Parameter '{param_name}' has no type hint. Defaulting to ParameterType.STRING.")
        return ParameterType.STRING, None

    if origin_type is TypingList or origin_type is list: 
        param_type_enum = ParameterType.ARRAY
        list_args = get_args(actual_type) 
        if list_args and len(list_args) == 1: 
            array_item_js_schema = _python_type_to_json_schema(list_args[0])
        if not array_item_js_schema: 
            array_item_js_schema = True 
        return param_type_enum, array_item_js_schema

    mapped_type = _TYPE_MAPPING.get(actual_type)
    if mapped_type:
        item_schema_for_array = True if mapped_type == ParameterType.ARRAY else None
        return mapped_type, item_schema_for_array

    logger.warning(f"Unmapped type hint {py_type} (actual_type: {actual_type}) for param '{param_name}'. Defaulting to ParameterType.STRING.")
    return ParameterType.STRING, None

def _parse_signature(sig: inspect.Signature, tool_name: str) -> Tuple[TypingList[str], bool, bool, ParameterSchema]:
    func_param_names = []
    expects_context = False
    expects_tool_state = False
    generated_arg_schema = ParameterSchema()

    for param_name, param_obj in sig.parameters.items():
        if param_name == "context":
            expects_context = True
            continue
        if param_name == "tool_state":
            expects_tool_state = True
            continue
        
        func_param_names.append(param_name)
        
        param_type_hint = param_obj.annotation
        param_type_enum, item_schema = _get_parameter_type_from_hint(param_type_hint, param_name)
        
        is_required = param_obj.default == inspect.Parameter.empty
        if get_origin(param_type_hint) is Union and type(None) in get_args(param_type_hint):
            is_required = False

        param_desc = f"Parameter '{param_name}' for tool '{tool_name}'."
        param_name_lower = param_name.lower()
        if "path" in param_name_lower or "file" in param_name_lower or "dir" in param_name_lower or "folder" in param_name_lower:
            param_desc += " This is expected to be a path."
            
        schema_param = ParameterDefinition(
            name=param_name,
            param_type=param_type_enum,
            description=param_desc,
            required=is_required,
            default_value=param_obj.default if param_obj.default != inspect.Parameter.empty else None,
            array_item_schema=item_schema
        )
        generated_arg_schema.add_parameter(schema_param)
        
    return func_param_names, expects_context, expects_tool_state, generated_arg_schema

# --- The refactored @tool decorator ---

def tool(
    _func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    argument_schema: Optional[ParameterSchema] = None,
    config_schema: Optional[ParameterSchema] = None
):
    def decorator(func: Callable) -> FunctionalTool:
        tool_name = name or func.__name__
        func_doc = inspect.getdoc(func)
        tool_desc = description or (func_doc.split('\n\n')[0] if func_doc else f"Functional tool: {tool_name}")
        
        sig = inspect.signature(func)
        is_async = inspect.iscoroutinefunction(func)
        func_param_names, expects_context, expects_tool_state, gen_arg_schema = _parse_signature(sig, tool_name)
        
        final_arg_schema = argument_schema if argument_schema is not None else gen_arg_schema

        def factory(inst_config: Optional[ToolConfig] = None) -> FunctionalTool:
            return FunctionalTool(
                original_func=func,
                name=tool_name,
                description=tool_desc,
                argument_schema=final_arg_schema,
                config_schema=config_schema,
                is_async=is_async,
                expects_context=expects_context,
                expects_tool_state=expects_tool_state,
                func_param_names=func_param_names,
                instantiation_config=inst_config.params if inst_config else None
            )
        
        # The decorator's responsibility is now just to assemble the raw metadata
        # and create the definition. It does NOT generate usage strings.
        tool_def = ToolDefinition(
            name=tool_name,
            description=tool_desc,
            argument_schema=final_arg_schema,
            config_schema=config_schema,
            custom_factory=factory,
            tool_class=None,
            category=ToolCategory.LOCAL
        )
        default_tool_registry.register_tool(tool_def)
        
        # Return a ready-to-use instance of the tool.
        return factory()

    if _func is None:
        return decorator
    else:
        return decorator(_func)
