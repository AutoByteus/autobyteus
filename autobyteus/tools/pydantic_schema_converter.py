# file: autobyteus/autobyteus/tools/pydantic_to_parameter_schema.py
import logging
from typing import Type, get_origin, get_args, Union, List, Dict
from pydantic import BaseModel
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

logger = logging.getLogger(__name__)

_PYDANTIC_TYPE_MAP = {
    str: ParameterType.STRING,
    int: ParameterType.INTEGER,
    float: ParameterType.FLOAT,
    bool: ParameterType.BOOLEAN,
    dict: ParameterType.OBJECT,
    list: ParameterType.ARRAY,
}

def pydantic_to_parameter_schema(pydantic_model: Type[BaseModel]) -> ParameterSchema:
    """
    Converts a Pydantic BaseModel into an AutoByteUs ParameterSchema.

    This function inspects the Pydantic model's fields and recursively builds a
    corresponding ParameterSchema, handling nested models and lists of models.

    Args:
        pydantic_model: The Pydantic model class to convert.

    Returns:
        A fully constructed ParameterSchema object.
    """
    schema = ParameterSchema()
    required_fields = {name for name, field_info in pydantic_model.model_fields.items() if field_info.is_required()}

    for field_name, field_info in pydantic_model.model_fields.items():
        param_type = ParameterType.STRING # Default
        object_schema = None
        array_item_schema = None
        
        # Determine if the type is Optional (e.g., Union[str, None])
        is_optional = False
        field_type = field_info.annotation
        origin_type = get_origin(field_type)
        
        if origin_type is Union:
            union_args = get_args(field_type)
            if type(None) in union_args:
                is_optional = True
            # Get the non-None type from the Union
            non_none_args = [arg for arg in union_args if arg is not type(None)]
            if len(non_none_args) == 1:
                field_type = non_none_args[0]
                origin_type = get_origin(field_type)
        
        if origin_type is list or origin_type is List:
            param_type = ParameterType.ARRAY
            list_item_type = get_args(field_type)[0] if get_args(field_type) else any
            if isinstance(list_item_type, type) and issubclass(list_item_type, BaseModel):
                # FIX: Recursively call the converter for the nested Pydantic model.
                array_item_schema = pydantic_to_parameter_schema(list_item_type)
            else:
                # Fallback for list of primitives
                primitive_type_str = _PYDANTIC_TYPE_MAP.get(list_item_type, ParameterType.STRING).value
                array_item_schema = {"type": primitive_type_str}
        
        elif isinstance(field_type, type) and issubclass(field_type, BaseModel):
            param_type = ParameterType.OBJECT
            # Recursively convert the nested Pydantic model
            object_schema = pydantic_to_parameter_schema(field_type)
        else:
            param_type = _PYDANTIC_TYPE_MAP.get(field_type, ParameterType.STRING)

        schema.add_parameter(ParameterDefinition(
            name=field_name,
            param_type=param_type,
            description=field_info.description or f"Parameter '{field_name}'.",
            required=field_name in required_fields and not is_optional,
            object_schema=object_schema,
            array_item_schema=array_item_schema
        ))

    return schema
