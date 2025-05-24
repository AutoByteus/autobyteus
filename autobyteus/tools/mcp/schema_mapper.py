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
        "number": ParameterType.FLOAT, # JSON Schema 'number' typically maps to float
        "boolean": ParameterType.BOOLEAN,
        # Note: 'object' and 'array' MCP types are handled by structure, not direct mapping.
        # If an MCP schema uses 'object' or 'array' for a top-level parameter (not the main input schema),
        # it would likely map to ParameterType.STRING (expecting JSON string) unless flattened.
    }
    
    # Heuristics for path parameters based on name and format
    _PATH_PARAM_NAMES = {"path", "filepath", "file_path", "filename", "file"}
    _DIR_PATH_PARAM_NAMES = {"folder", "dir", "directory", "dir_path", "directory_path", "save_dir", "output_dir"}
    _URI_FORMATS = {"uri", "url"}


    def map_to_autobyteus_schema(self, mcp_json_schema: Dict[str, Any]) -> ParameterSchema:
        """
        Maps an MCP JSON schema (typically for tool inputs) to an AutoByteUs ParameterSchema.

        Args:
            mcp_json_schema: The MCP JSON schema dictionary.

        Returns:
            An AutoByteUs ParameterSchema.
        
        Raises:
            ValueError: If the MCP schema is malformed or an unsupported structure is encountered.
        """
        if not isinstance(mcp_json_schema, dict):
            logger.error(f"MCP JSON schema must be a dictionary, got {type(mcp_json_schema)}.")
            raise ValueError("MCP JSON schema must be a dictionary.")

        logger.debug(f"Mapping MCP JSON schema to AutoByteUs ParameterSchema. MCP Schema: {mcp_json_schema}")
        
        autobyteus_schema = ParameterSchema()

        schema_type = mcp_json_schema.get("type")
        if schema_type != "object":
            # If the root schema is not an object, it implies the tool might take a single primitive
            # or an array directly. AutoByteUs ParameterSchema is designed around named parameters
            # typically derived from an object schema's properties.
            # For this case, we could:
            # 1. Wrap it: Create a single parameter in ParameterSchema named 'input_value' or similar.
            # 2. Error: State that only root 'object' type schemas are supported for mapping.
            # The design implies mapping `tool.input_schema` which is usually an object.
            # Let's assume for now that the root is 'object'. If not, it's an unhandled case by current design.
            logger.warning(f"MCP JSON schema root 'type' is '{schema_type}', not 'object'. "
                           "Mapping may be incomplete or incorrect for non-object root schemas.")
            # If it's a primitive type at root, we could potentially create a single parameter.
            # This part of mapping needs clarification if such schemas are common for MCP tools.
            # For now, only processing "object" type with "properties".
            if schema_type in self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP:
                 # Create a single parameter, e.g., named "input"
                 param_def = ParameterDefinition(
                     name="input_value", # Default name for single root primitive
                     param_type=self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP[schema_type],
                     description=mcp_json_schema.get("description", "Input value for the tool."),
                     required=True, # Assuming if it's the sole input, it's required
                     default_value=mcp_json_schema.get("default"),
                     enum_values=mcp_json_schema.get("enum") if schema_type == "string" else None
                 )
                 autobyteus_schema.add_parameter(param_def)
                 return autobyteus_schema
            else: # e.g. array at root. How to map this to named parameters?
                logger.error(f"Unsupported root schema type '{schema_type}' for direct mapping to ParameterSchema properties.")
                raise ValueError(f"MCP JSON schema root 'type' must be 'object' for typical mapping, got '{schema_type}'.")


        properties = mcp_json_schema.get("properties")
        if not isinstance(properties, dict):
            logger.warning("MCP JSON schema of type 'object' has no 'properties' or 'properties' is not a dict. Resulting ParameterSchema will be empty.")
            return autobyteus_schema # Empty schema

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
            # JSON schema format hint
            format_hint = param_mcp_schema.get("format", "").lower()


            autobyteus_param_type: Optional[ParameterType] = None

            # Heuristic for file/directory paths based on name and format
            param_name_lower = param_name.lower()
            if mcp_param_type_str == "string":
                if format_hint in self._URI_FORMATS and "path" in format_hint : # e.g. "uri-reference" that is a file path
                     if param_name_lower in self._DIR_PATH_PARAM_NAMES :
                        autobyteus_param_type = ParameterType.DIRECTORY_PATH
                     else: # Default to file path for uri-like things if name suggests path
                        autobyteus_param_type = ParameterType.FILE_PATH
                elif param_name_lower in self._FILE_PATH_NAMES:
                    autobyteus_param_type = ParameterType.FILE_PATH
                elif param_name_lower in self._DIR_PATH_PARAM_NAMES:
                    autobyteus_param_type = ParameterType.DIRECTORY_PATH
            
            if autobyteus_param_type is None: # If not determined by path heuristic
                if mcp_param_type_str in self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP:
                    autobyteus_param_type = self._MCP_TYPE_TO_AUTOBYTEUS_TYPE_MAP[mcp_param_type_str]
                    if autobyteus_param_type == ParameterType.STRING and enum_values:
                        autobyteus_param_type = ParameterType.ENUM
                elif mcp_param_type_str == "array" or mcp_param_type_str == "object":
                    # For complex types (array, object) not directly mappable to simple ParameterTypes,
                    # we map them to STRING, expecting a JSON string representation.
                    # This aligns with how LLMs often handle complex inputs for tools.
                    autobyteus_param_type = ParameterType.STRING
                    description += " (Expects a JSON string for complex data)"
                    logger.debug(f"MCP parameter '{param_name}' of type '{mcp_param_type_str}' will be mapped to "
                                 f"AutoByteUs ParameterType.STRING, expecting JSON string.")
                else:
                    logger.warning(f"Unsupported MCP parameter type '{mcp_param_type_str}' for parameter '{param_name}'. Defaulting to STRING.")
                    autobyteus_param_type = ParameterType.STRING
            
            # Ensure enum_values is a list of strings if param_type is ENUM
            if autobyteus_param_type == ParameterType.ENUM:
                if not enum_values or not isinstance(enum_values, list) or not all(isinstance(ev, str) for ev in enum_values):
                    logger.warning(f"Parameter '{param_name}' is ENUM type but 'enum' field is missing, not a list, or not list of strings in MCP schema. Problematic. Schema: {enum_values}")
                    # Fallback or error? For now, try to proceed, ParameterDefinition might complain.
                    # Or, convert to string type if enum values are bad.
                    # autobyteus_param_type = ParameterType.STRING 
                    # enum_values = None # Clear it if problematic

            try:
                param_def = ParameterDefinition(
                    name=param_name,
                    param_type=autobyteus_param_type,
                    description=description,
                    required=(param_name in required_params),
                    default_value=default_value,
                    enum_values=enum_values if autobyteus_param_type == ParameterType.ENUM else None,
                    # Min/max/pattern can be added if mcp_json_schema supports them directly (e.g. minimum, maximum, pattern keywords)
                    min_value=param_mcp_schema.get("minimum"),
                    max_value=param_mcp_schema.get("maximum"),
                    pattern=param_mcp_schema.get("pattern") if mcp_param_type_str == "string" else None
                )
                autobyteus_schema.add_parameter(param_def)
            except ValueError as e:
                 logger.error(f"Failed to create ParameterDefinition for '{param_name}': {e}. MCP schema for param: {param_mcp_schema}")
                 # Decide: skip param, or raise error for entire schema mapping?
                 # For now, skipping problematic param.
                 continue


        logger.debug(f"Successfully mapped MCP schema to AutoByteUs ParameterSchema with {len(autobyteus_schema.parameters)} parameters.")
        return autobyteus_schema
