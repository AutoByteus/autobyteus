# file: autobyteus/tools/tool_meta.py
import logging
from abc import ABCMeta
from typing import Dict, Any 

from autobyteus.tools.registry import default_tool_registry, ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema

logger = logging.getLogger(__name__)

class ToolMeta(ABCMeta):
    """
    Metaclass for BaseTool that automatically registers concrete tool subclasses
    ...
    """
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        # Skip registration for special classes that are not meant to be standalone tools.
        # FunctionalTool is now the explicit wrapper but shouldn't be registered itself.
        if name in ['BaseTool', 'GenericMcpTool', 'FunctionalTool'] or getattr(cls, "__abstractmethods__", None):
             logger.debug(f"Skipping registration for abstract or special tool class: {name}")
             return

        try:
            # Use the class itself to get the metadata, not an instance.
            tool_name = cls.get_name()
            if not tool_name or not isinstance(tool_name, str):
                logger.error(f"Tool class {name} must return a valid string from static get_name(). Skipping registration.")
                return

            general_description = cls.get_description()
            if not general_description or not isinstance(general_description, str):
                 logger.error(f"Tool class {name} ({tool_name}) must return a valid string from get_description(). Skipping registration.")
                 return

            argument_schema: ParameterSchema = None 
            try:
                argument_schema = cls.get_argument_schema() 
                if argument_schema is not None and not isinstance(argument_schema, ParameterSchema): 
                    logger.error(f"Tool class {name} ({tool_name}) get_argument_schema() must return a ParameterSchema or None. Got {type(argument_schema)}. Skipping registration.")
                    return
                logger.debug(f"Tool class {name} ({tool_name}) provided argument_schema with {len(argument_schema) if argument_schema else 0} parameters.")
            except Exception as e:
                logger.error(f"Tool class {name} ({tool_name}) failed to provide argument_schema via get_argument_schema(): {e}. Skipping registration.", exc_info=True)
                return
            
            usage_xml = cls.tool_usage_xml() 
            if not usage_xml or not isinstance(usage_xml, str):
                 logger.error(f"Tool class {name} ({tool_name}) failed to generate usage_xml via tool_usage_xml(). Skipping registration.")
                 return

            usage_json_dict: Dict[str, Any] = None
            try:
                usage_json_dict = cls.tool_usage_json()
                if not usage_json_dict or not isinstance(usage_json_dict, dict):
                    logger.error(f"Tool class {name} ({tool_name}) failed to generate a valid usage_json_dict via tool_usage_json(). Skipping registration.")
                    return
            except Exception as e:
                 logger.error(f"Tool class {name} ({tool_name}) failed during tool_usage_json(): {e}. Skipping registration.", exc_info=True)
                 return

            instantiation_config_schema: ParameterSchema = None 
            if hasattr(cls, 'get_config_schema'):
                try:
                    instantiation_config_schema = cls.get_config_schema()
                    if instantiation_config_schema is not None and not isinstance(instantiation_config_schema, ParameterSchema): 
                        logger.warning(f"Tool class {name} ({tool_name}) get_config_schema() returned non-ParameterSchema type: {type(instantiation_config_schema)}. Treating as no config schema.")
                        instantiation_config_schema = None
                    if instantiation_config_schema:
                         logger.debug(f"Tool class {name} ({tool_name}) provided instantiation_config_schema with {len(instantiation_config_schema)} parameters.")
                except Exception as e:
                    logger.warning(f"Tool class {name} ({tool_name}) has get_config_schema() but it failed: {e}. Assuming no instantiation config.")
            
            definition = ToolDefinition(
                name=tool_name, 
                description=general_description, 
                tool_class=cls, # Standard tools are registered with a class
                custom_factory=None, # And no custom factory
                argument_schema=argument_schema, 
                usage_xml=usage_xml,
                usage_json_dict=usage_json_dict,
                config_schema=instantiation_config_schema 
            )
            default_tool_registry.register_tool(definition)
            
            arg_schema_info = f"args: {len(argument_schema) if argument_schema else '0'}"
            config_info = f"inst_config: {len(instantiation_config_schema) if instantiation_config_schema else '0'}"
            logger.info(f"Auto-registered tool: '{tool_name}' from class {name} ({arg_schema_info}, {config_info})")

        except AttributeError as e:
             logger.error(f"Tool class {name} is missing a required method ({e}). Skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register tool class {name}: {e}", exc_info=True)
