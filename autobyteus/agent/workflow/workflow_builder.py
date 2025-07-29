# file: autobyteus/autobyteus/agent/workflow/workflow_builder.py
import logging
from typing import List, Optional, Dict

from .agentic_workflow import AgenticWorkflow
from .context.workflow_config import WorkflowConfig
from .context.workflow_node_config import WorkflowNodeConfig
from ...agent.context.agent_config import AgentConfig
from .factory.workflow_factory import WorkflowFactory

logger = logging.getLogger(__name__)

class WorkflowBuilder:
    """
    A fluent API for constructing and configuring an AgenticWorkflow.
    
    This builder simplifies the process of creating a workflow by abstracting
    away the manual creation of WorkflowConfig and WorkflowNodeConfig objects,
    and providing a more intuitive way to define the agent graph and its
    dependencies.

    Example:
        researcher_config = AgentConfig(name="Researcher", ...)
        writer_config = AgentConfig(name="Writer", ...)

        workflow = (
            WorkflowBuilder(description="Create a blog post about topic X.")
            .set_coordinator(researcher_config)
            .add_node(writer_config, dependencies=[researcher_config])
            .build()
        )
    """
    def __init__(self, description: str):
        """
        Initializes the WorkflowBuilder.

        Args:
            description: A high-level description of the workflow's goal.
        """
        if not description or not isinstance(description, str):
            raise ValueError("Workflow description must be a non-empty string.")

        self._description = description
        self._nodes: Dict[AgentConfig, List[AgentConfig]] = {}
        self._coordinator_config: Optional[AgentConfig] = None
        logger.info(f"WorkflowBuilder initialized for workflow: '{description[:50]}...'")

    def add_node(self, agent_config: AgentConfig, dependencies: Optional[List[AgentConfig]] = None) -> 'WorkflowBuilder':
        """
        Adds a regular agent node to the workflow.

        Args:
            agent_config: The configuration for the agent at this node.
            dependencies: A list of AgentConfig objects for nodes that this
                          node depends on. These dependencies must have been
                          added to the builder previously.

        Returns:
            The builder instance for fluent chaining.
        """
        if not isinstance(agent_config, AgentConfig):
            raise TypeError("agent_config must be an instance of AgentConfig.")
        
        if agent_config in self._nodes or agent_config == self._coordinator_config:
            raise ValueError(f"AgentConfig for '{agent_config.name}' has already been added to the workflow.")

        # Validate that dependencies have already been added
        if dependencies:
            for dep_config in dependencies:
                if dep_config not in self._nodes and dep_config != self._coordinator_config:
                    raise ValueError(f"Dependency agent '{dep_config.name}' must be added to the builder before being used as a dependency.")

        self._nodes[agent_config] = dependencies or []
        logger.debug(f"Added node '{agent_config.name}' to builder with {len(dependencies or [])} dependencies.")
        return self

    def set_coordinator(self, agent_config: AgentConfig) -> 'WorkflowBuilder':
        """
        Sets the coordinator agent for the workflow.

        A workflow can only have one coordinator. This agent is typically the
        entry point for tasks and is responsible for delegating to other nodes.

        Args:
            agent_config: The configuration for the coordinator agent.

        Returns:
            The builder instance for fluent chaining.
        """
        if self._coordinator_config is not None:
            raise ValueError("A coordinator has already been set for this workflow.")
            
        if not isinstance(agent_config, AgentConfig):
            raise TypeError("agent_config must be an instance of AgentConfig.")

        self._coordinator_config = agent_config
        logger.debug(f"Set coordinator for workflow to '{agent_config.name}'.")
        return self

    def build(self) -> AgenticWorkflow:
        """
        Constructs and returns the final AgenticWorkflow instance using the
        singleton WorkflowFactory.

        This method validates the workflow structure, builds the dependency graph,
        creates the necessary configuration objects, and then delegates the final
        instantiation to the factory.

        Returns:
            A configured and ready-to-use AgenticWorkflow instance.
            
        Raises:
            ValueError: If the workflow configuration is invalid (e.g., no coordinator set).
        """
        logger.info("Building AgenticWorkflow from builder...")
        if self._coordinator_config is None:
            raise ValueError("Cannot build workflow: A coordinator must be set using set_coordinator().")

        # Step 1: Create a map from AgentConfig to a new WorkflowNodeConfig instance
        node_map: Dict[AgentConfig, WorkflowNodeConfig] = {}
        all_configs = list(self._nodes.keys()) + [self._coordinator_config]
        
        for config in all_configs:
            # Create node configs without dependencies for now
            node_map[config] = WorkflowNodeConfig(agent_config=config)
        
        # Step 2: Build the dependency graph by linking the created nodes
        all_nodes_with_deps = self._nodes.copy()
        
        for agent_cfg, dep_cfgs in all_nodes_with_deps.items():
            current_node = node_map[agent_cfg]
            dependency_nodes = [node_map[dep_cfg] for dep_cfg in dep_cfgs]
            current_node.dependencies = dependency_nodes

        # Step 3: Create the final WorkflowConfig
        final_nodes = list(node_map.values())
        coordinator_node_instance = node_map[self._coordinator_config]

        workflow_config = WorkflowConfig(
            nodes=final_nodes,
            coordinator_node=coordinator_node_instance,
            description=self._description
        )
        
        logger.info(f"WorkflowConfig created successfully. Total nodes: {len(final_nodes)}. Coordinator: '{coordinator_node_instance.name}'.")

        # Step 4: Use the factory to instantiate and return the AgenticWorkflow
        factory = WorkflowFactory()
        return factory.create_workflow(config=workflow_config)
