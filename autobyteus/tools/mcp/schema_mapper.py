# file: autobyteus/autobyteus/tools/mcp/schema_mapper.py
import logging
from typing import Dict, Any, List, Optional

from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

logger = logging.getLogger(__name__)

class McpSchemaMapper:
    """
    Converts MCP tool JSON schemas to AutoByteUs ParameterSchema,
    handling nested object structures recursively.
    """

    _MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP = {
        "string": ParameterType.STRING,
        "integer": ParameterType.INTEGER,
        "number": ParameterType.FLOAT, 
        "boolean": ParameterType.BOOLEAN,
        "object": ParameterType.OBJECT, 
        "array": ParameterType.ARRAY,   
    }

    def map_to_autobyteus_schema(self, mcp_json_schema: Dict[str, Any]) -> ParameterSchema:
        if not isinstance(mcp_json_schema, dict):
            logger.error(f"MCP JSON schema must be a dictionary, got {type(mcp_json_schema)}.")
            raise ValueError("MCP JSON schema must be a dictionary.")

        logger.debug(f"Mapping MCP JSON schema to AutoByteUs ParameterSchema. MCP Schema: {mcp_json_schema}")
        
        autobyteus_schema = ParameterSchema()

        schema_type = mcp_json_schema.get("type")
        if schema_type != "object":
            logger.error(f"Unsupported root schema type '{schema_type}' for mapping to ParameterSchema. Must be 'object'.")
            raise ValueError(f"MCP JSON schema root 'type' must be 'object', got '{schema_type}'.")

        properties = mcp_json_schema.get("properties")
        if not isinstance(properties, dict):
            logger.warning("MCP JSON schema of type 'object' has no 'properties'. Resulting ParameterSchema will be empty.")
            return autobyteus_schema 
        
        # FIX: The 'required' list is specific to its own schema level.
        required_params_at_this_level: List[str] = mcp_json_schema.get("required", [])

        for param_name, param_mcp_schema in properties.items():
            if not isinstance(param_mcp_schema, dict):
                logger.warning(f"Property '{param_name}' in MCP schema is not a dictionary. Skipping.")
                continue

            mcp_param_type_str = param_mcp_schema.get("type")
            description = param_mcp_schema.get("description", f"Parameter '{param_name}'.")
            
            nested_object_schema: Optional[ParameterSchema] = None
            item_schema_for_array: Optional[Dict[str, Any]] = None

            if mcp_param_type_str == "object" and "properties" in param_mcp_schema:
                # Recursively map the nested object schema. The recursive call will handle its own 'required' list.
                nested_object_schema = self.map_to_autobyteus_schema(param_mcp_schema)
            
            elif mcp_param_type_str == "array":
                item_schema_for_array = param_mcp_schema.get("items", True)
            
            autobyteus_param_type = self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP.get(mcp_param_type_str, ParameterType.STRING)
            enum_values = param_mcp_schema.get("enum")
            if autobyteus_param_type == ParameterType.STRING and enum_values: 
                autobyteus_param_type = ParameterType.ENUM

            try:
                param_def = ParameterDefinition(
                    name=param_name,
                    param_type=autobyteus_param_type,
                    description=description,
                    required=(param_name in required_params_at_this_level), # FIX: Use the list for the current level.
                    default_value=param_mcp_schema.get("default"),
                    enum_values=enum_values if autobyteus_param_type == ParameterType.ENUM else None,
                    min_value=param_mcp_schema.get("minimum"),
                    max_value=param_mcp_schema.get("maximum"),
                    pattern=param_mcp_schema.get("pattern"),
                    array_item_schema=item_schema_for_array,
                    object_schema=nested_object_schema,
                )
                autobyteus_schema.add_parameter(param_def)
            except ValueError as e:
                 logger.error(f"Failed to create ParameterDefinition for '{param_name}': {e}.")
                 continue

        logger.debug(f"Successfully mapped MCP schema to ParameterSchema with {len(autobyteus_schema.parameters)} params.")
        return autobyteus_schema
