import inspect
import logging
import asyncio 
from typing import Callable, Optional, Any, Dict, Union, get_origin, get_args, List as TypingList

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext # Type hint only for context param
from autobyteus.tools.tool_config import ToolConfig # For type hinting in NewToolClass __init__

logger = logging.getLogger(__name__)

_TYPE_MAPPING = {
    # str is handled specially below for path inference
    int: ParameterType.INTEGER,
    float: ParameterType.FLOAT,
    bool: ParameterType.BOOLEAN,
    list: ParameterType.STRING, 
    dict: ParameterType.STRING, 
}

_FILE_PATH_NAMES = {"path", "filepath", "file_path", "filename"}
_DIR_PATH_NAMES = {"folder", "dir", "directory", "dir_path", "directory_path", "save_dir", "output_dir"}

def _get_parameter_type_from_hint(py_type: Any, param_name: str) -> ParameterType:
    origin_type = get_origin(py_type)
    actual_type = py_type

    if origin_type is Union: 
        args = get_args(py_type)
        non_none_type_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_type_args) == 1: 
            actual_type = non_none_type_args[0]
            # Re-evaluate origin for the unwrapped type (e.g. Optional[List[str]])
            origin_type = get_origin(actual_type) 
        else:
            logger.warning(f"Complex Union type hint {py_type} for param '{param_name}' encountered. Defaulting to STRING.")
            return ParameterType.STRING
    
    if actual_type is inspect.Parameter.empty: # Handle cases where annotation is empty
        logger.warning(f"Parameter '{param_name}' has no type hint. Defaulting to ParameterType.STRING. Name-based path inference will be attempted.")
        actual_type = str # Treat as str for path name heuristics

    if origin_type is list or origin_type is TypingList: # Use TypingList for get_origin
        logger.debug(f"Type hint {py_type} (origin: {origin_type}) for param '{param_name}' mapped to ParameterType.STRING (as JSON string).")
        return ParameterType.STRING 
    if origin_type is dict or origin_type is Dict:  # Use Dict for get_origin
        logger.debug(f"Type hint {py_type} (origin: {origin_type}) for param '{param_name}' mapped to ParameterType.STRING (as JSON string).")
        return ParameterType.STRING

    if actual_type is str:
        param_name_lower = param_name.lower()
        if param_name_lower in _FILE_PATH_NAMES:
            logger.debug(f"Param '{param_name}' with type 'str' inferred as FILE_PATH due to name.")
            return ParameterType.FILE_PATH
        if param_name_lower in _DIR_PATH_NAMES:
            logger.debug(f"Param '{param_name}' with type 'str' inferred as DIRECTORY_PATH due to name.")
            return ParameterType.DIRECTORY_PATH
        logger.debug(f"Param '{param_name}' with type 'str' inferred as STRING.")
        return ParameterType.STRING

    mapped_type = _TYPE_MAPPING.get(actual_type)
    if mapped_type:
        return mapped_type

    logger.warning(f"Unmapped type hint {py_type} (actual_type: {actual_type}) for param '{param_name}'. Defaulting to ParameterType.STRING.")
    return ParameterType.STRING


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
            # Use the first paragraph of the docstring as description
            tool_description_to_register = func_doc.split('\n\n')[0] 
        else:
            tool_description_to_register = f"Functional tool: {tool_name_to_register}"
        
        sig = inspect.signature(func)
        is_async_func = inspect.iscoroutinefunction(func)
        
        # These are always derived from the actual function signature for calling purposes
        func_param_names_for_call = [] 
        expects_context_param = False 

        # This schema is generated if user doesn't provide one
        generated_argument_schema_if_needed = ParameterSchema()

        for param_name_sig, param_obj_sig in sig.parameters.items():
            # Check for AgentContext parameter
            is_special_context_param = False
            if param_name_sig == "context":
                if param_obj_sig.annotation is AgentContext or \
                   (isinstance(param_obj_sig.annotation, str) and \
                    param_obj_sig.annotation in ('AgentContext', 'autobyteus.agent.context.AgentContext')):
                    is_special_context_param = True
                # Allow untyped 'context' parameter to also be treated as AgentContext for functional tools
                elif param_obj_sig.annotation == inspect.Parameter.empty:
                    is_special_context_param = True 
                    logger.debug(
                        f"Tool '{tool_name_to_register}': Untyped parameter 'context' "
                        "assumed to be AgentContext. Will be injected."
                    )
            
            if is_special_context_param:
                expects_context_param = True
                logger.debug(
                    f"Tool '{tool_name_to_register}': Parameter '{param_name_sig}' "
                    f"(annotation: '{param_obj_sig.annotation}') recognized as AgentContext. "
                    "Will be injected, not part of tool's argument schema."
                )
                continue 
            
            # This parameter is part of the function call signature (excluding context)
            func_param_names_for_call.append(param_name_sig)

            # If argument_schema is not user-provided, generate it from signature
            if not argument_schema:
                param_type_hint = param_obj_sig.annotation
                parameter_type_enum = _get_parameter_type_from_hint(param_type_hint, param_name_sig)
                
                is_required = (param_obj_sig.default == inspect.Parameter.empty)
                
                # Refined check for Optional making a parameter not required
                # An explicit default value (even None) also makes it not required if default is inspect.Parameter.empty
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
                    default_value=param_obj_sig.default if param_obj_sig.default != inspect.Parameter.empty else None
                )
                generated_argument_schema_if_needed.add_parameter(schema_param)
        
        # Determine the final argument schema for the tool definition
        final_argument_schema_for_tool_def = argument_schema if argument_schema else generated_argument_schema_if_needed
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
            _tool_reg_config_schema = config_schema # Stored from decorator argument
            _tool_reg_is_async = is_async_func
            _tool_reg_original_func = func
            _tool_reg_func_param_names = func_param_names_for_call
            _tool_reg_expects_context = expects_context_param

            def __init__(self, **kwargs: Any): # Accepts instantiation config parameters
                super().__init__()
                # Stores the resolved configuration values for this instance
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
                # Returns the config_schema passed to the decorator
                return cls._tool_reg_config_schema

            async def _execute(self, context: AgentContext, **kwargs: Any) -> Any:
                # kwargs here are execution arguments, already validated by BaseTool.execute
                # against _tool_reg_argument_schema.
                # self._functional_tool_instance_config holds instantiation configuration.

                call_args = {} # Arguments to be passed to the original Python function
                
                # Populate call_args from the execution kwargs, based on what the
                # original Python function actually expects (func_param_names_for_call).
                for p_name in self._tool_reg_func_param_names:
                    if p_name in kwargs: 
                        call_args[p_name] = kwargs[p_name]
                    # Note: If a required func param is not in kwargs (and not defaulted by Python func itself),
                    # this will lead to a runtime error when calling original_func.
                    # This should be caught by schema validation if schema is accurate.
                
                if self._tool_reg_expects_context:
                    call_args['context'] = context
                
                # Currently, self._functional_tool_instance_config is not automatically
                # passed to the original_func. The original_func would need to be
                # designed to accept these, e.g., via its own **kwargs or a specific config dict.
                # This could be a future enhancement if needed.

                if self._tool_reg_is_async:
                    return await self._tool_reg_original_func(**call_args)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, lambda: self._tool_reg_original_func(**call_args))

        NewToolClass.__name__ = dynamic_class_name_str
        NewToolClass.__qualname__ = dynamic_class_name_str 
        NewToolClass.__module__ = func.__module__ 

        logger.info(
            f"Dynamically created tool class '{dynamic_class_name_str}' for function "
            f"'{func.__name__}' to be registered as tool '{tool_name_to_register}'."
        )
        # ToolMeta will handle the registration with default_tool_registry
        return NewToolClass 

    return decorator
