# file: autobyteus/autobyteus/agent_team/agent_team_builder.py
import logging
from typing import List, Optional, Dict, Union, Set

from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
from autobyteus.agent_team.context.team_node_config import TeamNodeConfig
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent_team.factory.agent_team_factory import AgentTeamFactory
from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode

logger = logging.getLogger(__name__)

# Define a type hint for the possible definition types for clarity
NodeDefinition = Union[AgentConfig, AgentTeamConfig]

class AgentTeamBuilder:
    """
    A fluent API for constructing and configuring an AgentTeam.
    
    This builder simplifies creating an agent team by abstracting away the manual
    creation of config objects and providing an intuitive way to define the
    agent and sub-team graph. It enforces that all nodes within the team have
    a unique name.
    """
    def __init__(self, name: str, description: str, role: Optional[str] = None):
        """
        Initializes the AgentTeamBuilder.

        Args:
            name: A unique name for the agent team.
            description: A high-level description of the team's goal.
            role: An optional role description for when this team is used
                  as a sub-team within a parent.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Agent team name must be a non-empty string.")
        if not description or not isinstance(description, str):
            raise ValueError("Agent team description must be a non-empty string.")

        self._name = name
        self._description = description
        self._role = role
        self._nodes: Dict[NodeDefinition, List[NodeDefinition]] = {}
        self._coordinator_config: Optional[AgentConfig] = None
        self._added_node_names: Set[str] = set()
        self._task_notification_mode: TaskNotificationMode = TaskNotificationMode.AGENT_MANUAL_NOTIFICATION
        self._use_xml_tool_format: Optional[bool] = None
        logger.info(f"AgentTeamBuilder initialized for team: '{self._name}'.")

    def add_agent_node(self, agent_config: AgentConfig, dependencies: Optional[List[NodeDefinition]] = None) -> 'AgentTeamBuilder':
        """
        Adds a regular agent node to the agent team.

        Args:
            agent_config: The configuration for the agent at this node.
            dependencies: A list of AgentConfig or AgentTeamConfig objects for nodes 
                          that this node depends on. These must have been added previously.

        Returns:
            The builder instance for fluent chaining.
        """
        self._add_node_internal(agent_config, dependencies)
        return self

    def add_sub_team_node(self, team_config: AgentTeamConfig, dependencies: Optional[List[NodeDefinition]] = None) -> 'AgentTeamBuilder':
        """
        Adds a sub-team node to the agent team.

        Args:
            team_config: The configuration for the sub-team.
            dependencies: A list of AgentConfig or AgentTeamConfig objects for nodes 
                          that this node depends on. These must have been added previously.

        Returns:
            The builder instance for fluent chaining.
        """
        self._add_node_internal(team_config, dependencies)
        return self

    def _add_node_internal(self, node_definition: NodeDefinition, dependencies: Optional[List[NodeDefinition]]):
        """Internal helper to add a node of any type."""
        if not isinstance(node_definition, (AgentConfig, AgentTeamConfig)):
            raise TypeError("node_definition must be an instance of AgentConfig or AgentTeamConfig.")
        
        node_name = node_definition.name
        if node_name in self._added_node_names:
            # Enforce unique names. This is the new, simpler validation.
            raise ValueError(f"Duplicate node name '{node_name}' detected. All nodes in a team must have a unique name.")

        if node_definition in self._nodes or node_definition == self._coordinator_config:
            raise ValueError(f"The exact same node definition object for '{node_name}' has already been added to the team.")

        if dependencies:
            for dep_config in dependencies:
                if dep_config not in self._nodes and dep_config != self._coordinator_config:
                    raise ValueError(f"Dependency node '{dep_config.name}' must be added to the builder before being used as a dependency.")

        self._nodes[node_definition] = dependencies or []
        self._added_node_names.add(node_name)
        
        node_type = "Sub-Team" if isinstance(node_definition, AgentTeamConfig) else "Agent"
        logger.debug(f"Added {node_type} node '{node_name}' to builder with {len(dependencies or [])} dependencies.")

    def set_coordinator(self, agent_config: AgentConfig) -> 'AgentTeamBuilder':
        """
        Sets the coordinator agent for the team. A coordinator must be an agent.

        Args:
            agent_config: The configuration for the coordinator agent.

        Returns:
            The builder instance for fluent chaining.
        """
        if self._coordinator_config is not None:
            raise ValueError("A coordinator has already been set for this team.")
            
        if not isinstance(agent_config, AgentConfig):
            raise TypeError("Coordinator must be an instance of AgentConfig.")
            
        node_name = agent_config.name
        if node_name in self._added_node_names:
            raise ValueError(f"Duplicate node name '{node_name}' detected. The coordinator's name must also be unique within the team.")

        self._coordinator_config = agent_config
        self._added_node_names.add(node_name)
        logger.debug(f"Set coordinator for team to '{agent_config.name}'.")
        return self

    def set_task_notification_mode(self, mode: TaskNotificationMode) -> 'AgentTeamBuilder':
        """
        Sets the task notification mode for the team.

        Args:
            mode: The desired TaskNotificationMode (AGENT_MANUAL_NOTIFICATION or SYSTEM_EVENT_DRIVEN).

        Returns:
            The builder instance for fluent chaining.
        """
        if not isinstance(mode, TaskNotificationMode):
            raise TypeError("mode must be an instance of TaskNotificationMode.")
        self._task_notification_mode = mode
        logger.debug(f"Task notification mode set to '{mode.value}'.")
        return self

    def set_use_xml_tool_format(self, use_xml: bool) -> 'AgentTeamBuilder':
        """
        Sets the team-level override for using XML tool format.

        If set, this will override the setting on all individual agents within the team.

        Args:
            use_xml: If True, forces the team to use XML format for tool
                     definitions and parsing.

        Returns:
            The builder instance for fluent chaining.
        """
        if not isinstance(use_xml, bool):
            raise TypeError("use_xml must be a boolean.")
        self._use_xml_tool_format = use_xml
        logger.debug(f"Team-level XML tool format override set to '{use_xml}'.")
        return self

    def build(self) -> AgentTeam:
        """
        Constructs and returns the final AgentTeam instance using the
        singleton AgentTeamFactory.
        """
        logger.info("Building AgentTeam from builder...")
        if self._coordinator_config is None:
            raise ValueError("Cannot build team: A coordinator must be set.")

        node_map: Dict[NodeDefinition, TeamNodeConfig] = {}
        # Ensure the coordinator config is also in the set of definitions to process
        all_definitions = list(self._nodes.keys())
        if self._coordinator_config not in all_definitions:
             all_definitions.append(self._coordinator_config)
        
        for definition in all_definitions:
            node_map[definition] = TeamNodeConfig(node_definition=definition)
        
        for node_def, dep_defs in self._nodes.items():
            if node_def in node_map and dep_defs:
                current_node = node_map[node_def]
                dependency_nodes = [node_map[dep_def] for dep_def in dep_defs]
                current_node.dependencies = tuple(dependency_nodes)

        final_nodes = list(node_map.values())
        coordinator_node_instance = node_map[self._coordinator_config]

        team_config = AgentTeamConfig(
            name=self._name,
            description=self._description,
            role=self._role,
            nodes=tuple(final_nodes),
            coordinator_node=coordinator_node_instance,
            task_notification_mode=self._task_notification_mode,
            use_xml_tool_format=self._use_xml_tool_format
        )
        
        logger.info(f"AgentTeamConfig created successfully. Name: '{team_config.name}'. Total nodes: {len(final_nodes)}. Coordinator: '{coordinator_node_instance.name}'.")

        factory = AgentTeamFactory()
        return factory.create_team(config=team_config)
