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
        "object": ParameterType.OBJECT, # New mapping
        "array": ParameterType.ARRAY,   # New mapping
    }
    
    _PATH_PARAM_NAMES = {"path", "filepath", "file_path", "filename", "file"}
    _DIR_PATH_PARAM_NAMES = {"folder", "dir", "directory", "dir_path", "directory_path", "save_dir", "output_dir"}
    _URI_FORMATS = {"uri", "url"}


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
            if schema_type in self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP:
                 param_type_enum = self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP[schema_type]
                 array_item_schema_for_root: Optional[Dict[str, Any]] = None
                 if param_type_enum == ParameterType.ARRAY:
                     array_item_schema_for_root = mcp_json_schema.get("items", True) # Default to generic array

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
            format_hint = param_mcp_schema.get("format", "").lower()
            
            # For array types, get the item schema
            item_schema_for_array: Optional[Dict[str, Any]] = None
            if mcp_param_type_str == "array":
                item_schema_for_array = param_mcp_schema.get("items")
                if item_schema_for_array is None: # If "items" is not specified, default to generic array items
                    item_schema_for_array = True 
                    logger.debug(f"MCP parameter '{param_name}' is 'array' type with no 'items' schema. Defaulting to generic items (true).")


            autobyteus_param_type: Optional[ParameterType] = None

            param_name_lower = param_name.lower()
            if mcp_param_type_str == "string":
                if format_hint in self._URI_FORMATS and "path" in format_hint : 
                     if param_name_lower in self._DIR_PATH_PARAM_NAMES :
                        autobyteus_param_type = ParameterType.DIRECTORY_PATH
                     else: 
                        autobyteus_param_type = ParameterType.FILE_PATH
                elif param_name_lower in self._FILE_PATH_NAMES:
                    autobyteus_param_type = ParameterType.FILE_PATH
                elif param_name_lower in self._DIR_PATH_PARAM_NAMES:
                    autobyteus_param_type = ParameterType.DIRECTORY_PATH
            
            if autobyteus_param_type is None: # If not determined by path heuristic
                if mcp_param_type_str in self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP:
                    autobyteus_param_type = self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP[mcp_param_type_str]
                    if autobyteus_param_type == ParameterType.STRING and enum_values: # String with enum becomes ENUM type
                        autobyteus_param_type = ParameterType.ENUM
                # No fallback to STRING for unmapped complex types anymore, as OBJECT and ARRAY are now mapped.
                # If a type is truly unmapped by _MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP, it's an issue.
                elif mcp_param_type_str: # If type string is present but not in map
                    logger.warning(f"Unsupported MCP parameter type '{mcp_param_type_str}' for parameter '{param_name}'. Defaulting to STRING.")
                    autobyteus_param_type = ParameterType.STRING
                else: # No type string provided
                    logger.warning(f"MCP parameter '{param_name}' has no 'type' specified. Defaulting to STRING.")
                    autobyteus_param_type = ParameterType.STRING
            
            if autobyteus_param_type == ParameterType.ENUM:
                if not enum_values or not isinstance(enum_values, list) or not all(isinstance(ev, str) for ev in enum_values):
                    logger.warning(f"Parameter '{param_name}' is ENUM type but 'enum' field is missing, not a list, or not list of strings in MCP schema. Problematic. Schema: {enum_values}")

            try:
                param_def = ParameterDefinition(
                    name=param_name,
                    param_type=autobyteus_param_type,
                    description=description,
                    required=(param_name in required_params),
                    default_value=default_value,
                    enum_values=enum_values if autobyteus_param_type == ParameterType.ENUM else None,
                    min_value=param_mcp_schema.get("minimum"),
                    max_value=param_mcp_schema.get("maximum"),
                    pattern=param_mcp_schema.get("pattern") if mcp_param_type_str == "string" else None,
                    array_item_schema=item_schema_for_array # Pass item schema for array types
                )
                autobyteus_schema.add_parameter(param_def)
            except ValueError as e:
                 logger.error(f"Failed to create ParameterDefinition for '{param_name}': {e}. MCP schema for param: {param_mcp_schema}")
                 continue

        logger.debug(f"Successfully mapped MCP schema to AutoByteUs ParameterSchema with {len(autobyteus_schema.parameters)} parameters.")
        return autobyteus_schema
