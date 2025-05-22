# file: autobyteus/autobyteus/agent/registry/agent_definition_meta.py
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent.registry.agent_definition_registry import AgentDefinitionRegistry # For type hint
    from autobyteus.agent.registry.agent_definition import AgentDefinition # For type hint

logger = logging.getLogger(__name__)

class AgentDefinitionMeta(type):
    """
    Metaclass for AgentDefinition that automatically registers instances
    with the default_definition_registry_instance upon their creation.
    """
    def __call__(cls, *args, **kwargs) -> 'AgentDefinition':
        """
        Called when an instance of a class using this metaclass is created
        (e.g., AgentDefinition(...)).
        """
        # Create the instance using the parent's __call__ (which calls __new__ and __init__)
        instance = super().__call__(*args, **kwargs)
        
        # Dynamically import the default registry instance to avoid circular imports at module level
        try:
            from autobyteus.agent.registry.agent_registry import default_definition_registry_instance
        except ImportError: # pragma: no cover
            logger.error(
                "Failed to import default_definition_registry_instance from autobyteus.agent.registry.agent_registry. "
                "AgentDefinition auto-registration will be skipped."
            )
            return instance # Return instance without registration if import fails

        if default_definition_registry_instance is not None:
            try:
                # Assuming 'instance' is a fully initialized AgentDefinition object here
                # and has 'name' and 'role' attributes.
                default_definition_registry_instance.register(instance)
                logger.info(
                    f"Auto-registered AgentDefinition instance: '{instance.name}' (Role: '{instance.role}') "
                    f"with key '{default_definition_registry_instance._generate_key(instance.name, instance.role)}'."
                )
            except AttributeError: # pragma: no cover 
                # This might happen if instance is not a valid AgentDefinition or if default_definition_registry_instance is malformed
                logger.error(
                    f"Failed to auto-register AgentDefinition. Instance might be malformed or registry is not standard. Instance: {str(instance)[:100]}",
                    exc_info=True
                )
            except Exception as e: # pragma: no cover
                logger.error(
                    f"An unexpected error occurred during auto-registration of AgentDefinition '{getattr(instance, 'name', 'Unknown')}': {e}",
                    exc_info=True
                )
        else: # pragma: no cover
            # This case should ideally not be hit if the application structure is correct
            # and default_definition_registry_instance is always initialized.
            logger.error(
                "Default AgentDefinitionRegistry instance (default_definition_registry_instance) is None. "
                "Cannot auto-register AgentDefinition instance."
            )
            
        return instance
