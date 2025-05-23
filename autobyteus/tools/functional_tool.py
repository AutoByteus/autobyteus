import inspect
import logging
import asyncio # Added for loop.run_in_executor in _execute
from typing import Callable, Optional, Any, Dict, Union, get_origin, get_args, List # ADDED List HERE

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

_TYPE_MAPPING = {
    str: ParameterType.STRING,
    int: ParameterType.INTEGER,
    float: ParameterType.FLOAT,
    bool: ParameterType.BOOLEAN,
    list: ParameterType.STRING, 
    dict: ParameterType.STRING, 
}

def _get_parameter_type_from_hint(py_type: Any) -> ParameterType:
    origin_type = get_origin(py_type)
    
    if origin_type is Union: 
        args = get_args(py_type)
        non_none_type_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_type_args) == 1: 
            return _get_parameter_type_from_hint(non_none_type_args[0])
        else:
            logger.warning(f"Complex Union type hint {py_type} encountered. Defaulting to STRING.")
            return ParameterType.STRING
            
    if origin_type is list or origin_type is List: 
        logger.debug(f"Type hint {py_type} (origin: {origin_type}) mapped to ParameterType.STRING (as JSON string).")
        return ParameterType.STRING 
    if origin_type is dict or origin_type is Dict: 
        logger.debug(f"Type hint {py_type} (origin: {origin_type}) mapped to ParameterType.STRING (as JSON string).")
        return ParameterType.STRING

    mapped_type = _TYPE_MAPPING.get(py_type)
    if mapped_type:
        return mapped_type

    logger.warning(f"Unmapped type hint {py_type}. Defaulting to ParameterType.STRING.")
    return ParameterType.STRING


def tool(name: Optional[str] = None, description: Optional[str] = None):
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
        
        generated_argument_schema = ParameterSchema()
        func_param_names_for_call = [] 
        expects_context_param = False 

        for param_name, param_obj in sig.parameters.items():
            if param_name == "context":
                is_agent_context_param = (param_obj.annotation == AgentContext or 
                                          (param_obj.annotation == inspect.Parameter.empty and param_name == "context"))
                if is_agent_context_param:
                    expects_context_param = True
                    logger.debug(f"Tool '{tool_name_to_register}': Parameter '{param_name}' recognized as AgentContext. Will be injected, not part of schema.")
                    continue 
            
            func_param_names_for_call.append(param_name)

            param_type_hint = param_obj.annotation
            if param_type_hint == inspect.Parameter.empty:
                logger.warning(f"Tool '{tool_name_to_register}': Parameter '{param_name}' has no type hint. Defaulting to ParameterType.STRING.")
                parameter_type_enum = ParameterType.STRING
            else:
                parameter_type_enum = _get_parameter_type_from_hint(param_type_hint)
            
            is_required = (param_obj.default == inspect.Parameter.empty)
            
            origin_type = get_origin(param_type_hint)
            if origin_type is Union:
                args = get_args(param_type_hint)
                if type(None) in args: 
                    is_required = False 
            
            param_desc_for_schema = f"Parameter '{param_name}' for tool '{tool_name_to_register}'."

            schema_param = ParameterDefinition(
                name=param_name,
                param_type=parameter_type_enum,
                description=param_desc_for_schema,
                required=is_required,
                default_value=param_obj.default if param_obj.default != inspect.Parameter.empty else None
            )
            generated_argument_schema.add_parameter(schema_param)
        
        dynamic_class_name_str = f"{tool_name_to_register.capitalize().replace('_','')}FunctionalToolClass"
        
        class NewToolClass(BaseTool):
            _tool_reg_name = tool_name_to_register
            _tool_reg_description = tool_description_to_register
            _tool_reg_argument_schema = generated_argument_schema
            _tool_reg_is_async = is_async_func
            _tool_reg_original_func = func
            _tool_reg_func_param_names = func_param_names_for_call
            _tool_reg_expects_context = expects_context_param

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
                return None

            async def _execute(self, context: AgentContext, **kwargs: Any) -> Any:
                call_args = {}
                for p_name in self._tool_reg_func_param_names:
                    if p_name in kwargs: 
                        call_args[p_name] = kwargs[p_name]
                
                if self._tool_reg_expects_context:
                    call_args['context'] = context
                
                if self._tool_reg_is_async:
                    return await self._tool_reg_original_func(**call_args)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, lambda: self._tool_reg_original_func(**call_args))

        NewToolClass.__name__ = dynamic_class_name_str
        NewToolClass.__qualname__ = dynamic_class_name_str 
        NewToolClass.__module__ = func.__module__ 

        logger.info(f"Dynamically created tool class '{dynamic_class_name_str}' for function '{func.__name__}' to be registered as tool '{tool_name_to_register}'.")
        return NewToolClass 

    return decorator
