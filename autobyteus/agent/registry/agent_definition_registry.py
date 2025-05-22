# file: autobyteus/autobyteus/agent/registry/agent_definition_registry.py
import logging
from typing import Dict, List, Optional, Union, Tuple

from .agent_definition import AgentDefinition

logger = logging.getLogger(__name__)

class AgentDefinitionRegistry:
    """
    A registry for storing and managing AgentDefinition objects.

    This registry uses a composite key generated from the `name` and `role`
    attributes of an AgentDefinition. The key format is "name::role".
    It is a non-singleton class, allowing multiple instances if needed, and is
    not directly tied to agent instantiation or factories, focusing solely on
    the management of definitions.
    """

    _KEY_SEPARATOR = "::"

    def __init__(self):
        """Initializes the AgentDefinitionRegistry with an empty store."""
        self._definitions: Dict[str, AgentDefinition] = {}
        logger.info("AgentDefinitionRegistry initialized.")

    def _generate_key(self, name: str, role: str) -> str:
        """Generates the composite key for storing/retrieving definitions."""
        if not name: # Should be caught by AgentDefinition validation, but good for direct calls
            raise ValueError("Definition name cannot be empty for key generation.")
        if not role: # Should be caught by AgentDefinition validation
            raise ValueError("Definition role cannot be empty for key generation.")
        return f"{name}{self._KEY_SEPARATOR}{role}"

    def register(self, definition: AgentDefinition) -> None:
        """
        Registers an agent definition.

        If a definition with the same composite key (name::role) already exists,
        it will be overwritten, and a warning will be logged.

        Args:
            definition: The AgentDefinition object to register.

        Raises:
            ValueError: If the definition's name or role is empty (via _generate_key).
        """
        # AgentDefinition constructor already validates name and role are non-empty.
        composite_key = self._generate_key(definition.name, definition.role)
        
        if composite_key in self._definitions:
            logger.warning(f"Overwriting existing agent definition for key: '{composite_key}'.")
        
        self._definitions[composite_key] = definition
        logger.info(f"AgentDefinition '{definition.name}' (role: '{definition.role}') registered successfully with key '{composite_key}'.")

    def get(self, name: str, role: str) -> Optional[AgentDefinition]:
        """
        Retrieves an agent definition by its name and role.

        Args:
            name: The name of the agent definition.
            role: The role of the agent definition.

        Returns:
            The AgentDefinition object if found, otherwise None.
        """
        if not isinstance(name, str) or not name:
            logger.warning("Attempted to retrieve definition with invalid or empty name.")
            return None
        if not isinstance(role, str) or not role:
            logger.warning("Attempted to retrieve definition with invalid or empty role.")
            return None
            
        composite_key = self._generate_key(name, role)
        definition = self._definitions.get(composite_key)
        if not definition:
            logger.debug(f"AgentDefinition with key '{composite_key}' (name: '{name}', role: '{role}') not found in registry.")
        return definition

    def unregister(self, name: str, role: str) -> bool:
        """
        Removes an agent definition from the registry by its name and role.

        Args:
            name: The name of the agent definition.
            role: The role of the agent definition.

        Returns:
            True if the definition was successfully removed, False otherwise (e.g., if not found).
        """
        if not isinstance(name, str) or not name:
            logger.warning("Attempted to unregister definition with invalid or empty name.")
            return False
        if not isinstance(role, str) or not role:
            logger.warning("Attempted to unregister definition with invalid or empty role.")
            return False
            
        composite_key = self._generate_key(name, role)
        if composite_key in self._definitions:
            retrieved_def = self._definitions.pop(composite_key) 
            logger.info(f"AgentDefinition '{retrieved_def.name}' (role: '{retrieved_def.role}') with key '{composite_key}' unregistered successfully.")
            return True
        else:
            logger.warning(f"AgentDefinition with key '{composite_key}' (name: '{name}', role: '{role}') not found for unregistration.")
            return False

    def get_all(self) -> Dict[str, AgentDefinition]:
        """
        Returns a shallow copy of the dictionary containing all registered agent definitions.
        Keys are composite strings "name::role".

        Returns:
            A dictionary where keys are composite definition keys and values are AgentDefinition objects.
        """
        return dict(self._definitions)

    def list_names(self) -> List[str]:
        """
        Returns a list of composite keys (name::role) of all registered agent definitions.

        Returns:
            A list of strings, where each string is a composite key.
        """
        return list(self._definitions.keys())

    def list_all(self) -> List[AgentDefinition]:
        """
        Returns a list of all registered AgentDefinition objects.

        Returns:
            A list of AgentDefinition objects.
        """
        return list(self._definitions.values())

    def clear(self) -> None:
        """Removes all definitions from the registry."""
        count = len(self._definitions)
        self._definitions.clear()
        logger.info(f"Cleared {count} definitions from the AgentDefinitionRegistry.")

    def __len__(self) -> int:
        """Returns the number of registered agent definitions."""
        return len(self._definitions)

    def __contains__(self, item: Union[str, AgentDefinition, Tuple[str, str]]) -> bool:
        """
        Checks if a definition is in the registry.
        Can check by:
        - AgentDefinition object (uses its name and role to build the key).
        - Tuple[str, str] (name, role).
        - Composite key string (e.g., "name::role").
        """
        composite_key: Optional[str] = None
        if isinstance(item, AgentDefinition):
            composite_key = self._generate_key(item.name, item.role)
        elif isinstance(item, tuple) and len(item) == 2 and all(isinstance(x, str) for x in item):
            # item is Tuple[str, str] for (name, role)
            name, role = item
            if not name or not role: # Prevent key generation with empty parts from tuple
                logger.debug(f"__contains__ check with tuple: name or role is empty. ('{name}', '{role}'). Returning False.")
                return False
            composite_key = self._generate_key(name, role)
        elif isinstance(item, str):
            # Assume item is the full composite key
            composite_key = item
        else:
            logger.debug(f"__contains__ check with unsupported type: {type(item)}. Returning False.")
            return False
        
        if composite_key:
            return composite_key in self._definitions
        return False # Should not happen if logic above is correct and item is one of accepted types

