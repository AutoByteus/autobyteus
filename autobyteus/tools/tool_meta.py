# file: autobyteus/tools/tool_meta.py
import logging
from abc import ABCMeta

# Import the global registry and definition class from the registry package
from autobyteus.tools.registry import default_tool_registry, ToolDefinition

logger = logging.getLogger(__name__) # Using __name__ for specific logger

class ToolMeta(ABCMeta):
    """
    Metaclass for BaseTool that automatically registers concrete tool subclasses
    with the default_tool_registry using their static name, usage description,
    optional config schema, and class reference obtained from class methods.
    """
    def __init__(cls, name, bases, dct):
        """
        Called when a class using this metaclass is defined.
        """
        super().__init__(name, bases, dct)

        # Prevent registration of the BaseTool class itself or other explicitly abstract classes
        if name == 'BaseTool' or getattr(cls, "__abstractmethods__", None):
             logger.debug(f"Skipping registration for abstract class: {name}")
             return

        try:
            # Get static/class info from the class being defined
            tool_name = cls.get_name()
            usage_description = cls.tool_usage()
            
            # Try to get config schema if the tool defines one
            config_schema = None
            if hasattr(cls, 'get_config_schema'):
                try:
                    config_schema = cls.get_config_schema()
                    logger.debug(f"Tool class {name} provided config schema with {len(config_schema) if config_schema else 0} parameters")
                except Exception as e:
                    logger.warning(f"Tool class {name} has get_config_schema() but it failed: {e}")

            # Basic validation of fetched static info
            if not tool_name or not isinstance(tool_name, str):
                logger.error(f"Tool class {name} must return a valid string from static get_name(). Skipping registration.")
                return
            if not usage_description or not isinstance(usage_description, str):
                 # Updated error message to reflect source method
                 logger.error(f"Tool class {name} must return a valid string from class method tool_usage(). Skipping registration.")
                 return

            # Create definition using name, usage description, class reference, and optional config schema
            definition = ToolDefinition(
                name=tool_name, 
                description=usage_description, 
                tool_class=cls,
                config_schema=config_schema
            )
            default_tool_registry.register_tool(definition)
            
            config_info = f" with {len(config_schema)} config parameters" if config_schema else " (no config)"
            logger.info(f"Auto-registered tool: '{tool_name}' from class {name}{config_info}")

        except AttributeError as e:
             # Catch if required methods are missing (get_name or tool_usage/tool_usage_xml)
             logger.error(f"Tool class {name} is missing required static/class method ({e}). Skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register tool class {name}: {e}", exc_info=True)
