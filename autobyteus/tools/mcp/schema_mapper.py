# file: autobyteus/autobyteus/mcp/schema_mapper.py
import logging
from typing import Dict, Any, List, Optional

from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

logger = logging.getLogger(__name__)

class McpSchemaMapper:
    """
    Converts MCP tool JSON schemas to AutoByteUs ParameterSchema.
    """

    _MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP = {
        "string": ParameterType.STRING,
        "integer": ParameterType.INTEGER,
        "number": ParameterType.FLOAT, 
        "boolean": ParameterType.BOOLEAN,
        "object": ParameterType.OBJECT, 
        "array": ParameterType.ARRAY,   
    }
    
    # REMOVED: _FILE_PATH_NAMES, _DIR_PATH_PARAM_NAMES, _URI_FORMATS
    # as FILE_PATH and DIRECTORY_PATH types are removed.
    # All string-based path parameters will now be ParameterType.STRING.
    # The 'format' hint from MCP schema (e.g., "uri", "url") will still be available
    # on the ParameterDefinition if it includes 'pattern', but it won't change the type from STRING.

    def map_to_autobyteus_schema(self, mcp_json_schema: Dict[str, Any]) -> ParameterSchema:
        if not isinstance(mcp_json_schema, dict):
            logger.error(f"MCP JSON schema must be a dictionary, got {type(mcp_json_schema)}.")
            raise ValueError("MCP JSON schema must be a dictionary.")

        logger.debug(f"Mapping MCP JSON schema to AutoByteUs ParameterSchema. MCP Schema: {mcp_json_schema}")
        
        autobyteus_schema = ParameterSchema()

        schema_type = mcp_json_schema.get("type")
        if schema_type != "object":
            logger.warning(f"MCP JSON schema root 'type' is '{schema_type}', not 'object'. "
                           "Mapping may be incomplete or incorrect for non-object root schemas.")
            if schema_type in McpSchemaMapper._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP:
                 param_type_enum = McpSchemaMapper._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP[schema_type]
                 array_item_schema_for_root: Optional[Dict[str, Any]] = None
                 if param_type_enum == ParameterType.ARRAY:
                     array_item_schema_for_root = mcp_json_schema.get("items", True) 

                 param_def = ParameterDefinition(
                     name="input_value", 
                     param_type=param_type_enum,
                     description=mcp_json_schema.get("description", "Input value for the tool."),
                     required=True, 
                     default_value=mcp_json_schema.get("default"),
                     enum_values=mcp_json_schema.get("enum") if schema_type == "string" else None,
                     array_item_schema=array_item_schema_for_root
                 )
                 autobyteus_schema.add_parameter(param_def)
                 return autobyteus_schema
            else: 
                logger.error(f"Unsupported root schema type '{schema_type}' for direct mapping to ParameterSchema properties.")
                raise ValueError(f"MCP JSON schema root 'type' must be 'object' for typical mapping, got '{schema_type}'.")


        properties = mcp_json_schema.get("properties")
        if not isinstance(properties, dict):
            logger.warning("MCP JSON schema of type 'object' has no 'properties' or 'properties' is not a dict. Resulting ParameterSchema will be empty.")
            return autobyteus_schema 

        required_params: List[str] = mcp_json_schema.get("required", [])
        if not isinstance(required_params, list) or not all(isinstance(p, str) for p in required_params):
            logger.warning("MCP JSON schema 'required' field is not a list of strings. Treating all params as optional.")
            required_params = []

        for param_name, param_mcp_schema in properties.items():
            if not isinstance(param_mcp_schema, dict):
                logger.warning(f"Property '{param_name}' in MCP schema is not a dictionary. Skipping this parameter.")
                continue

            mcp_param_type_str = param_mcp_schema.get("type")
            description = param_mcp_schema.get("description", f"Parameter '{param_name}'.")
            default_value = param_mcp_schema.get("default")
            enum_values = param_mcp_schema.get("enum")
            # format_hint is still read but won't be used to change type to FILE_PATH/DIR_PATH
            # format_hint = param_mcp_schema.get("format", "").lower() 
            
            item_schema_for_array: Optional[Dict[str, Any]] = None
            if mcp_param_type_str == "array":
                item_schema_for_array = param_mcp_schema.get("items")
                if item_schema_for_array is None: 
                    item_schema_for_array = True 
                    logger.debug(f"MCP parameter '{param_name}' is 'array' type with no 'items' schema. Defaulting to generic items (true).")
            
            autobyteus_param_type: Optional[ParameterType] = None
            # REMOVED: Logic block that inferred FILE_PATH or DIRECTORY_PATH based on format_hint or param_name_lower.
            # All string types from MCP will now map to STRING or ENUM.

            if mcp_param_type_str in McpSchemaMapper._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP:
                autobyteus_param_type = McpSchemaMapper._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP[mcp_param_type_str]
                if autobyteus_param_type == ParameterType.STRING and enum_values: 
                    autobyteus_param_type = ParameterType.ENUM
            elif mcp_param_type_str: 
                logger.warning(f"Unsupported MCP parameter type '{mcp_param_type_str}' for parameter '{param_name}'. Defaulting to STRING.")
                autobyteus_param_type = ParameterType.STRING
            else: 
                logger.warning(f"MCP parameter '{param_name}' has no 'type' specified. Defaulting to STRING.")
                autobyteus_param_type = ParameterType.STRING
            
            if autobyteus_param_type == ParameterType.ENUM:
                if not enum_values or not isinstance(enum_values, list) or not all(isinstance(ev, str) for ev in enum_values):
                    logger.warning(f"Parameter '{param_name}' is ENUM type but 'enum' field is missing, not a list, or not list of strings in MCP schema. Problematic. Schema: {enum_values}")

            try:
                param_def = ParameterDefinition(
                    name=param_name,
                    param_type=autobyteus_param_type, # This will now be STRING for former path types
                    description=description,
                    required=(param_name in required_params),
                    default_value=default_value,
                    enum_values=enum_values if autobyteus_param_type == ParameterType.ENUM else None,
                    min_value=param_mcp_schema.get("minimum"),
                    max_value=param_mcp_schema.get("maximum"),
                    pattern=param_mcp_schema.get("pattern") if mcp_param_type_str == "string" else None,
                    array_item_schema=item_schema_for_array 
                )
                autobyteus_schema.add_parameter(param_def)
            except ValueError as e:
                 logger.error(f"Failed to create ParameterDefinition for '{param_name}': {e}. MCP schema for param: {param_mcp_schema}")
                 continue

        logger.debug(f"Successfully mapped MCP schema to AutoByteUs ParameterSchema with {len(autobyteus_schema.parameters)} parameters.")
        return autobyteus_schema
