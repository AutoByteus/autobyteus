from __future__ import annotations

from typing import Optional

from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

from .module_manifest import ModuleManifest, ModuleArgument


_TYPE_MAP = {
    "string": ParameterType.STRING,
    "integer": ParameterType.INTEGER,
    "float": ParameterType.FLOAT,
    "number": ParameterType.FLOAT,
    "boolean": ParameterType.BOOLEAN,
    "array": ParameterType.ARRAY,
    "object": ParameterType.OBJECT,
}


def _resolve_parameter_type(arg: ModuleArgument) -> ParameterType:
    normalized = arg.type.lower().strip()
    return _TYPE_MAP.get(normalized, ParameterType.STRING)


def _build_definition(arg: ModuleArgument) -> ParameterDefinition:
    param_type = _resolve_parameter_type(arg)
    array_item_schema: Optional[dict] = None
    if param_type == ParameterType.ARRAY and arg.item_type:
        item = arg.item_type.lower().strip()
        array_item_schema = {"type": _TYPE_MAP.get(item, ParameterType.STRING).value}

    return ParameterDefinition(
        name=arg.name,
        param_type=param_type,
        description=arg.description,
        required=arg.required,
        default_value=arg.default,
        enum_values=arg.enum,
        array_item_schema=array_item_schema,
    )


def build_argument_schema(manifest: ModuleManifest) -> ParameterSchema:
    schema = ParameterSchema()
    for argument in manifest.arguments:
        schema.add_parameter(_build_definition(argument))
    return schema
