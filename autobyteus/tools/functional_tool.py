import inspect
import logging
import asyncio 
from typing import Callable, Optional, Any, Dict, Tuple, Union, get_origin, get_args, List as TypingList, TYPE_CHECKING

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
# from autobyteus.agent.context import AgentContext # Removed direct import
from autobyteus.tools.tool_config import ToolConfig # For type hinting in NewToolClass __init__

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Type hint only for context param

logger = logging.getLogger(__name__)

_TYPE_MAPPING = {
    # str is handled specially below for path inference
    int: ParameterType.INTEGER,
    float: ParameterType.FLOAT,
    bool: ParameterType.BOOLEAN,
    # list and dict will be handled by specific logic now
}

_FILE_PATH_NAMES = {"path", "filepath", "file_path", "filename"}
_DIR_PATH_NAMES = {"folder", "dir", "directory", "dir_path", "directory_path", "save_dir", "output_dir"}

def _python_type_to_json_schema(py_type: Any) -> Optional[Dict[str, Any]]:
    """
    Converts basic Python types to a simple JSON schema dictionary.
    Used for array item types.
    """
    if py_type is str:
        return {"type": "string"}
    if py_type is int:
        return {"type": "integer"}
    if py_type is float:
        return {"type": "number"}
    if py_type is bool:
        return {"type": "boolean"}
    if py_type is dict: # Generic dict
        return {"type": "object"}
    if py_type is list: # Generic list
        return {"type": "array", "items": True} # Array of any type
    
    origin_type = get_origin(py_type)
    if origin_type is Union:
        args = get_args(py_type)
        non_none_types = [t for t in args if t is not type(None)]
        if len(non_none_types) == 1: # Essentially an Optional[T]
            return _python_type_to_json_schema(non_none_types[0])
        # More complex unions (e.g., Union[str, int]) could be represented with "anyOf"
        # For simplicity, returning None here, or could default to generic object/string
        return None
    if origin_type is TypingList or origin_type is list:
        list_args = get_args(py_type)
        if list_args and len(list_args) == 1:
            item_schema = _python_type_to_json_schema(list_args[0])
            return {"type": "array", "items": item_schema if item_schema else True}
        return {"type": "array", "items": True} # Generic array
    if origin_type is Dict or origin_type is dict:
        # For Dict[K,V], JSON schema represents this as an object where keys are strings
        # and values have the type of V. If V is complex, this gets tricky.
        # For now, just "type": "object" for simplicity from basic type hints.
        return {"type": "object"}

    logger.debug(f"Could not map Python type {py_type} to a simple JSON schema for array items.")
    return None


def _get_parameter_type_from_hint(py_type: Any, param_name: str) -> Tuple[ParameterType, Optional[Dict[str, Any]]]:
    """
    Infers ParameterType and array_item_schema from Python type hint.
    Returns: (ParameterType, Optional[JSON schema dict for array items])
    """
    origin_type = get_origin(py_type)
    actual_type = py_type
    array_item_js_schema: Optional[Dict[str, Any]] = None

    if origin_type is Union: 
        args = get_args(py_type)
        non_none_type_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_type_args) == 1: 
            actual_type = non_none_type_args[0]
            origin_type = get_origin(actual_type) # Re-evaluate origin for the unwrapped type
        else:
            logger.warning(f"Complex Union type hint {py_type} for param '{param_name}' encountered. Defaulting to STRING.")
            return ParameterType.STRING, None # Treat as string if complex union
    
    if actual_type is inspect.Parameter.empty: # Handle cases where annotation is empty
        logger.warning(f"Parameter '{param_name}' has no type hint. Defaulting to ParameterType.STRING. Name-based path inference will be attempted.")
        actual_type = str # Treat as str for path name heuristics

    # Handle list (maps to ARRAY)
    if origin_type is TypingList or origin_type is list: # Check actual_type as well if origin_type is None (e.g. plain list)
        param_type_enum = ParameterType.ARRAY
        list_args = get_args(actual_type) # get_args works on List[T] or plain list if it was wrapped
        if list_args and len(list_args) == 1: # e.g. List[str]
            array_item_js_schema = _python_type_to_json_schema(list_args[0])
        if not array_item_js_schema: # Default for untyped list or unmappable item type
            array_item_js_schema = True # True means items can be of any type in JSON schema
        return param_type_enum, array_item_js_schema

    # Handle dict (maps to OBJECT)
    if origin_type is Dict or origin_type is dict: # Check actual_type as well
        return ParameterType.OBJECT, None # No array_item_schema for OBJECT

    # Handle str (can be STRING, FILE_PATH, DIRECTORY_PATH)
    if actual_type is str:
        param_name_lower = param_name.lower()
        if param_name_lower in _FILE_PATH_NAMES:
            return ParameterType.FILE_PATH, None
        if param_name_lower in _DIR_PATH_NAMES:
            return ParameterType.DIRECTORY_PATH, None
        return ParameterType.STRING, None

    # Handle other primitive types
    mapped_type = _TYPE_MAPPING.get(actual_type)
    if mapped_type:
        return mapped_type, None

    logger.warning(f"Unmapped type hint {py_type} (actual_type: {actual_type}) for param '{param_name}'. Defaulting to ParameterType.STRING.")
    return ParameterType.STRING, None


def tool(
    name: Optional[str] = None, 
    description: Optional[str] = None,
    argument_schema: Optional[ParameterSchema] = None,
    config_schema: Optional[ParameterSchema] = None
):
    def decorator(func: Callable):
        tool_name_to_register = name if name else func.__name__
        
        func_doc = inspect.getdoc(func)
        if description:
            tool_description_to_register = description
        elif func_doc:
            tool_description_to_register = func_doc.split('\n\n')[0] 
        else:
            tool_description_to_register = f"Functional tool: {tool_name_to_register}"
        
        sig = inspect.signature(func)
        is_async_func = inspect.iscoroutinefunction(func)
        
        func_param_names_for_call = [] 
        expects_context_param = False 

        generated_argument_schema_if_needed = ParameterSchema()

        for param_name_sig, param_obj_sig in sig.parameters.items():
            is_special_context_param = False
            if param_name_sig == "context":
                annotation_str = ""
                if isinstance(param_obj_sig.annotation, str):
                    annotation_str = param_obj_sig.annotation
                elif param_obj_sig.annotation != inspect.Parameter.empty:
                    try: 
                        annotation_str = f"{param_obj_sig.annotation.__module__}.{param_obj_sig.annotation.__qualname__}"
                    except AttributeError: 
                        annotation_str = str(param_obj_sig.annotation) 
                
                expected_context_annotations = (
                    'AgentContext', 
                    'autobyteus.agent.context.AgentContext',
                    'autobyteus.agent.context.agent_context.AgentContext' 
                )

                if annotation_str in expected_context_annotations:
                    is_special_context_param = True
                elif param_obj_sig.annotation == inspect.Parameter.empty: 
                    is_special_context_param = True
                    logger.debug(
                        f"Tool '{tool_name_to_register}': Untyped parameter 'context' "
                        "assumed to be AgentContext. Will be injected."
                    )
            
            if is_special_context_param:
                expects_context_param = True
                continue 
            
            func_param_names_for_call.append(param_name_sig)

            if not argument_schema:
                param_type_hint = param_obj_sig.annotation
                # Get ParameterType and array_item_schema (if applicable)
                parameter_type_enum, inferred_array_item_schema = _get_parameter_type_from_hint(param_type_hint, param_name_sig)
                
                is_required = (param_obj_sig.default == inspect.Parameter.empty)
                
                origin_type_check = get_origin(param_type_hint)
                if origin_type_check is Union:
                    args_union = get_args(param_type_hint)
                    if type(None) in args_union: 
                        is_required = False 
                
                param_desc_for_schema = f"Parameter '{param_name_sig}' for tool '{tool_name_to_register}'."

                schema_param = ParameterDefinition(
                    name=param_name_sig,
                    param_type=parameter_type_enum,
                    description=param_desc_for_schema,
                    required=is_required,
                    default_value=param_obj_sig.default if param_obj_sig.default != inspect.Parameter.empty else None,
                    array_item_schema=inferred_array_item_schema # Store inferred item schema
                )
                generated_argument_schema_if_needed.add_parameter(schema_param)
        
        final_argument_schema_for_tool_def = argument_schema if argument_schema else generated_argument_schema_if_needed
        # ... (rest of the decorator remains largely the same) ...
        if argument_schema:
             logger.info(f"Tool '{tool_name_to_register}': Using user-provided argument schema.")
        else:
             logger.info(f"Tool '{tool_name_to_register}': Generated argument schema from function signature.")

        if config_schema:
            logger.info(f"Tool '{tool_name_to_register}': Using user-provided config schema.")

        dynamic_class_name_str = f"{tool_name_to_register.capitalize().replace('_','')}FunctionalToolClass"
        
        class NewToolClass(BaseTool):
            _tool_reg_name = tool_name_to_register
            _tool_reg_description = tool_description_to_register
            _tool_reg_argument_schema = final_argument_schema_for_tool_def
            _tool_reg_config_schema = config_schema 
            _tool_reg_is_async = is_async_func
            _tool_reg_original_func = func # This stores the original, unbound function
            _tool_reg_func_param_names = func_param_names_for_call
            _tool_reg_expects_context = expects_context_param

            def __init__(self, **kwargs: Any): 
                super().__init__()
                self._functional_tool_instance_config: Dict[str, Any] = kwargs
                if self._functional_tool_instance_config:
                    logger.debug(
                        f"Functional tool wrapper '{self.get_name()}' instance "
                        f"created with config: {self._functional_tool_instance_config}"
                    )

            @classmethod
            def get_name(cls) -> str:
                return cls._tool_reg_name

            @classmethod
            def get_description(cls) -> str:
                return cls._tool_reg_description

            @classmethod
            def get_argument_schema(cls) -> Optional[ParameterSchema]:
                return cls._tool_reg_argument_schema
            
            @classmethod
            def get_config_schema(cls) -> Optional[ParameterSchema]: 
                return cls._tool_reg_config_schema

            async def _execute(self, context: 'AgentContext', **kwargs: Any) -> Any: 
                call_args = {}
                for p_name in self._tool_reg_func_param_names:
                    if p_name in kwargs: 
                        call_args[p_name] = kwargs[p_name]
                
                if self._tool_reg_expects_context:
                    call_args['context'] = context
                
                # Get the class of the current instance (self)
                current_class = type(self)

                if self._tool_reg_is_async:
                    # Call the original function via the class attribute to avoid implicit self binding
                    return await current_class._tool_reg_original_func(**call_args)
                else:
                    loop = asyncio.get_event_loop()
                    # Call the original function via the class attribute in the executor
                    # Ensure 'current_class' is available in the lambda's scope correctly
                    # or assign to a local variable before the lambda.
                    original_func_to_call = current_class._tool_reg_original_func
                    return await loop.run_in_executor(None, lambda: original_func_to_call(**call_args))

        NewToolClass.__name__ = dynamic_class_name_str
        NewToolClass.__qualname__ = dynamic_class_name_str 
        NewToolClass.__module__ = func.__module__ 

        logger.info(
            f"Dynamically created tool class '{dynamic_class_name_str}' for function "
            f"'{func.__name__}' to be registered as tool '{tool_name_to_register}'."
        )
        return NewToolClass 

    return decorator
