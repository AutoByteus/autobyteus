# file: autobyteus/autobyteus/workflow/workflow_builder.py
import logging
from typing import List, Optional, Dict, Union

from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.workflow.context.workflow_config import WorkflowConfig
from autobyteus.workflow.context.workflow_node_config import WorkflowNodeConfig
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.workflow.factory.workflow_factory import WorkflowFactory

logger = logging.getLogger(__name__)

# Define a type hint for the possible definition types for clarity
NodeDefinition = Union[AgentConfig, WorkflowConfig]

class WorkflowBuilder:
    """
    A fluent API for constructing and configuring an AgenticWorkflow.
    
    This builder simplifies creating a workflow by abstracting away the manual
    creation of config objects and providing an intuitive way to define the
    agent and sub-workflow graph.
    """
    def __init__(self, name: str, description: str, role: Optional[str] = None):
        """
        Initializes the WorkflowBuilder.

        Args:
            name: A unique name for the workflow.
            description: A high-level description of the workflow's goal.
            role: An optional role description for when this workflow is used
                  as a sub-workflow within a parent.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Workflow name must be a non-empty string.")
        if not description or not isinstance(description, str):
            raise ValueError("Workflow description must be a non-empty string.")

        self._name = name
        self._description = description
        self._role = role
        self._nodes: Dict[NodeDefinition, List[NodeDefinition]] = {}
        self._coordinator_config: Optional[AgentConfig] = None
        logger.info(f"WorkflowBuilder initialized for workflow: '{self._name}'.")

    def add_agent_node(self, agent_config: AgentConfig, dependencies: Optional[List[NodeDefinition]] = None) -> 'WorkflowBuilder':
        """
        Adds a regular agent node to the workflow.

        Args:
            agent_config: The configuration for the agent at this node.
            dependencies: A list of AgentConfig or WorkflowConfig objects for nodes 
                          that this node depends on. These must have been added previously.

        Returns:
            The builder instance for fluent chaining.
        """
        self._add_node_internal(agent_config, dependencies)
        return self

    def add_workflow_node(self, workflow_config: WorkflowConfig, dependencies: Optional[List[NodeDefinition]] = None) -> 'WorkflowBuilder':
        """
        Adds a sub-workflow node to the workflow.

        Args:
            workflow_config: The configuration for the sub-workflow.
            dependencies: A list of AgentConfig or WorkflowConfig objects for nodes 
                          that this node depends on. These must have been added previously.

        Returns:
            The builder instance for fluent chaining.
        """
        self._add_node_internal(workflow_config, dependencies)
        return self

    def _add_node_internal(self, node_definition: NodeDefinition, dependencies: Optional[List[NodeDefinition]]):
        """Internal helper to add a node of any type."""
        if not isinstance(node_definition, (AgentConfig, WorkflowConfig)):
            raise TypeError("node_definition must be an instance of AgentConfig or WorkflowConfig.")
        
        if node_definition in self._nodes or node_definition == self._coordinator_config:
            raise ValueError(f"Node definition for '{node_definition.name}' has already been added to the workflow.")

        if dependencies:
            for dep_config in dependencies:
                if dep_config not in self._nodes and dep_config != self._coordinator_config:
                    raise ValueError(f"Dependency node '{dep_config.name}' must be added to the builder before being used as a dependency.")

        self._nodes[node_definition] = dependencies or []
        node_type = "Sub-workflow" if isinstance(node_definition, WorkflowConfig) else "Agent"
        logger.debug(f"Added {node_type} node '{node_definition.name}' to builder with {len(dependencies or [])} dependencies.")

    def set_coordinator(self, agent_config: AgentConfig) -> 'WorkflowBuilder':
        """
        Sets the coordinator agent for the workflow. A coordinator must be an agent.

        Args:
            agent_config: The configuration for the coordinator agent.

        Returns:
            The builder instance for fluent chaining.
        """
        if self._coordinator_config is not None:
            raise ValueError("A coordinator has already been set for this workflow.")
            
        if not isinstance(agent_config, AgentConfig):
            raise TypeError("Coordinator must be an instance of AgentConfig.")

        self._coordinator_config = agent_config
        logger.debug(f"Set coordinator for workflow to '{agent_config.name}'.")
        return self

    def build(self) -> AgenticWorkflow:
        """
        Constructs and returns the final AgenticWorkflow instance using the
        singleton WorkflowFactory.
        """
        logger.info("Building AgenticWorkflow from builder...")
        if self._coordinator_config is None:
            raise ValueError("Cannot build workflow: A coordinator must be set.")

        node_map: Dict[NodeDefinition, WorkflowNodeConfig] = {}
        all_definitions = list(self._nodes.keys()) + [self._coordinator_config]
        
        for definition in all_definitions:
            node_map[definition] = WorkflowNodeConfig(node_definition=definition)
        
        all_nodes_with_deps = self._nodes.copy()
        all_nodes_with_deps[self._coordinator_config] = [] # Coordinator has no explicit deps in this model
        
        for node_def, dep_defs in all_nodes_with_deps.items():
            if node_def in node_map and dep_defs:
                current_node = node_map[node_def]
                dependency_nodes = [node_map[dep_def] for dep_def in dep_defs]
                current_node.dependencies = tuple(dependency_nodes)

        final_nodes = list(node_map.values())
        coordinator_node_instance = node_map[self._coordinator_config]

        workflow_config = WorkflowConfig(
            name=self._name,
            description=self._description,
            role=self._role,
            nodes=tuple(final_nodes),
            coordinator_node=coordinator_node_instance
        )
        
        logger.info(f"WorkflowConfig created successfully. Name: '{workflow_config.name}'. Total nodes: {len(final_nodes)}. Coordinator: '{coordinator_node_instance.name}'.")

        factory = WorkflowFactory()
        return factory.create_workflow(config=workflow_config)
