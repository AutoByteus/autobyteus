# file: autobyteus/autobyteus/tools/tool_meta.py
import logging
from abc import ABCMeta
from typing import Dict, Any 

from autobyteus.tools.registry import default_tool_registry, ToolDefinition
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

logger = logging.getLogger(__name__)

class ToolMeta(ABCMeta):
    """
    Metaclass for BaseTool that automatically registers concrete tool subclasses.
    """
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        # Skip registration for special classes that are not meant to be standalone tools.
        # FunctionalTool is an explicit wrapper but shouldn't be registered itself.
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

            # Note: We do not call the schema methods here. We pass them as providers.
            
            # Get category from class attribute, defaulting to "General"
            category_str = getattr(cls, 'CATEGORY', ToolCategory.GENERAL)
            
            # Create the definition without pre-generating usage strings
            definition = ToolDefinition(
                name=tool_name, 
                description=general_description, 
                tool_class=cls,
                custom_factory=None,
                argument_schema_provider=cls.get_argument_schema,
                config_schema_provider=cls.get_config_schema,
                origin=ToolOrigin.LOCAL,
                category=category_str
            )
            default_tool_registry.register_tool(definition)
            
            logger.info(f"Auto-registered tool: '{tool_name}' from class {name}")

        except AttributeError as e:
             logger.error(f"Tool class {name} is missing a required method ({e}). Skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register tool class {name}: {e}", exc_info=True)
