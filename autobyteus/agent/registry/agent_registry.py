# file: autobyteus/autobyteus/agent/registry/agent_registry.py
import logging
from typing import Dict, List, Optional

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.agent.factory.agent_factory import AgentFactory
from .agent_definition import AgentDefinition

logger = logging.getLogger(__name__)

class AgentRegistry(metaclass=SingletonMeta):
    """
    Manages AgentDefinitions (role, description, tools, initial_user_message, agent_class),
    populated exclusively via programmatic registration. Uses AgentFactory to create agent instances.
    """
    _definitions: Dict[str, AgentDefinition] = {}

    def __init__(self, agent_factory: AgentFactory):
        """
        Initializes the AgentRegistry with an AgentFactory.

        Args:
            agent_factory: The AgentFactory instance used to create agent instances.
        """
        self.agent_factory = agent_factory
        logger.info("AgentRegistry initialized with AgentFactory.")

    def register_agent(self, definition: AgentDefinition):
        """
        Registers an agent definition (role, description, tools, initial_user_message, agent_class) programmatically.

        Args:
            definition: The AgentDefinition object to register.

        Raises:
            ValueError: If the definition is invalid. Overwrites existing definitions with the same role.
        """
        if not isinstance(definition, AgentDefinition):
            raise ValueError("Attempted to register an object that is not an AgentDefinition.")

        role = definition.role
        if role in self._definitions:
            logger.warning(f"Overwriting existing agent definition for role: '{role}'")
        AgentRegistry._definitions[role] = definition
        logger.info(f"Successfully registered agent definition: '{role}'")

    def get_agent_definition(self, role: str) -> Optional[AgentDefinition]:
        """
        Retrieves the definition for a specific agent role.

        Args:
            role: The unique role of the agent definition to retrieve.

        Returns:
            The AgentDefinition object if found, otherwise None.
        """
        definition = self._definitions.get(role)
        if not definition:
            logger.debug(f"Agent definition not found for role: '{role}'")
        return definition

    def create_agent(self, role: str, agent_id: str):
        """
        Creates an agent instance using the AgentFactory based on the agent definition.

        Args:
            role: The role of the agent to create.
            agent_id: The unique identifier for the agent instance.

        Returns:
            The agent instance if the definition exists, otherwise None.

        Raises:
            ValueError: If the agent definition is not found.
        """
        definition = self.get_agent_definition(role)
        if not definition:
            logger.error(f"Cannot create agent: No definition found for role '{role}'")
            raise ValueError(f"No agent definition found for role '{role}'")
        
        logger.info(f"Creating agent instance for role '{role}' with id '{agent_id}' using AgentFactory")
        return self.agent_factory.create_agent(agent_id)

    def list_agents(self) -> List[AgentDefinition]:
        """
        Returns a list of all registered agent definitions.

        Returns:
            A list of AgentDefinition objects.
        """
        return list(self._definitions.values())

    def list_agent_roles(self) -> List[str]:
        """
        Returns a list of the roles of all registered agents.

        Returns:
            A list of agent role strings.
        """
        return list(self._definitions.keys())

    def get_all_definitions(self) -> Dict[str, AgentDefinition]:
        """Returns the internal dictionary of definitions."""
        return dict(AgentRegistry._definitions)

default_agent_registry = AgentRegistry(agent_factory=AgentFactory(
    role="default",
    agent_type="group_aware",
    tool_factory=ToolFactory(),
    llm_factory=LLMFactory(),
    prompt_builder=PromptBuilder(),
    llm_model=LLMModel(),
    tool_names=[]
))
