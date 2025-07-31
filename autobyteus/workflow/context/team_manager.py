# file: autobyteus/autobyteus/workflow/context/team_manager.py
import asyncio
import logging
from typing import List, Dict, Optional, TYPE_CHECKING, Union

from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.utils.wait_for_idle import wait_for_agent_to_be_idle
from autobyteus.workflow.utils.wait_for_idle import wait_for_workflow_to_be_idle
from autobyteus.workflow.exceptions import WorkflowNodeNotFoundException
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.tools.registry import default_tool_registry

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.workflow.agentic_workflow import AgenticWorkflow
    from autobyteus.workflow.events.workflow_events import InterAgentMessageRequestEvent
    from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime
    from autobyteus.workflow.streaming.agent_event_multiplexer import AgentEventMultiplexer
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.workflow.context.workflow_config import WorkflowConfig

ManagedNode = Union['Agent', 'AgenticWorkflow']

logger = logging.getLogger(__name__)

class TeamManager:
    """
    Manages all nodes (agents and sub-workflows) within a workflow. It handles
    lazy creation, on-demand startup, and provides access to managed instances.
    """
    def __init__(self, workflow_id: str, runtime: 'WorkflowRuntime', multiplexer: 'AgentEventMultiplexer'):
        self.workflow_id = workflow_id
        self._runtime = runtime
        self._multiplexer = multiplexer
        self._agent_factory = AgentFactory()
        self._nodes_cache: Dict[str, ManagedNode] = {}
        self._coordinator_agent: Optional['Agent'] = None
        logger.info(f"TeamManager created for workflow '{self.workflow_id}'.")

    async def dispatch_inter_agent_message_request(self, event: 'InterAgentMessageRequestEvent'):
        await self._runtime.submit_event(event)

    async def ensure_node_is_ready(self, name: str) -> ManagedNode:
        """
        Retrieves a node (agent or sub-workflow) by its unique friendly name.
        If the node has not been created yet, it is instantiated. If it is not
        running, it is started and awaited until idle.
        Returns a fully ready node instance or raises an exception.
        """
        node_instance = self._nodes_cache.get(name)
        
        was_created = False
        if not node_instance:
            logger.debug(f"Node '{name}' not in cache for workflow '{self.workflow_id}'. Attempting lazy creation.")
            
            node_config_wrapper = self._runtime.context.get_node_config_by_name(name)
            if not node_config_wrapper:
                raise WorkflowNodeNotFoundException(node_name=name, workflow_id=self.workflow_id)

            node_definition = node_config_wrapper.node_definition

            if node_config_wrapper.is_subworkflow:
                from autobyteus.workflow.factory.workflow_factory import WorkflowFactory
                from autobyteus.workflow.context.workflow_config import WorkflowConfig
                
                workflow_factory = WorkflowFactory() # Get singleton instance
                if not isinstance(node_definition, WorkflowConfig):
                     raise TypeError(f"Expected WorkflowConfig for node '{name}', but found {type(node_definition)}")
                logger.info(f"Lazily creating sub-workflow node '{name}' in workflow '{self.workflow_id}'.")
                node_instance = workflow_factory.create_workflow(config=node_definition)
            else:
                from autobyteus.agent.context.agent_config import AgentConfig
                if not isinstance(node_definition, AgentConfig):
                     raise TypeError(f"Expected AgentConfig for node '{name}', but found {type(node_definition)}")
                
                # --- Apply Deferred Logic from Bootstrap Step ---
                final_config = node_definition.copy()

                # 1. Inject SendMessageTo tool
                send_message_tool = default_tool_registry.create_tool(SendMessageTo.get_name())
                if isinstance(send_message_tool, SendMessageTo):
                    send_message_tool.set_team_manager(self)
                final_config.tools = [t for t in final_config.tools if not isinstance(t, SendMessageTo)]
                final_config.tools.append(send_message_tool)

                # 2. Apply coordinator prompt if this is the coordinator
                coordinator_node_name = self._runtime.context.config.coordinator_node.name
                if name == coordinator_node_name:
                    coordinator_prompt = self._runtime.context.state.prepared_coordinator_prompt
                    if coordinator_prompt:
                        final_config.system_prompt = coordinator_prompt
                        logger.info(f"Applied dynamic prompt to coordinator '{name}'.")
                
                logger.info(f"Lazily creating agent node '{name}' in workflow '{self.workflow_id}'.")
                node_instance = self._agent_factory.create_agent(config=final_config)
            
            self._nodes_cache[name] = node_instance
            was_created = True

        if was_created and node_instance:
            from autobyteus.workflow.agentic_workflow import AgenticWorkflow
            from autobyteus.agent.agent import Agent
            if isinstance(node_instance, AgenticWorkflow):
                self._multiplexer.start_bridging_workflow_events(node_instance, name)
            elif isinstance(node_instance, Agent):
                self._multiplexer.start_bridging_agent_events(node_instance, name)

        # On-Demand Startup Logic
        if not node_instance.is_running:
            from autobyteus.workflow.agentic_workflow import AgenticWorkflow
            logger.info(f"Workflow '{self.workflow_id}': Node '{name}' is not running. Starting on-demand.")
            try:
                node_instance.start()
                if isinstance(node_instance, AgenticWorkflow):
                    await wait_for_workflow_to_be_idle(node_instance, timeout=120.0)
                else:
                    await wait_for_agent_to_be_idle(node_instance, timeout=60.0)
            except Exception as e:
                logger.error(f"Workflow '{self.workflow_id}': Failed to start node '{name}' on-demand: {e}", exc_info=True)
                raise RuntimeError(f"Failed to start node '{name}' on-demand.") from e
        
        return node_instance

    def get_all_agents(self) -> List['Agent']:
        from autobyteus.agent.agent import Agent
        return [node for node in self._nodes_cache.values() if isinstance(node, Agent)]

    def get_all_sub_workflows(self) -> List['AgenticWorkflow']:
        from autobyteus.workflow.agentic_workflow import AgenticWorkflow
        return [node for node in self._nodes_cache.values() if isinstance(node, AgenticWorkflow)]

    @property
    def coordinator_agent(self) -> Optional['Agent']:
        return self._coordinator_agent

    async def ensure_coordinator_is_ready(self, coordinator_name: str) -> 'Agent':
        """
        Ensures the coordinator agent is created, started, and ready, then
        designates it as the coordinator.
        """
        from autobyteus.agent.agent import Agent
        node = await self.ensure_node_is_ready(coordinator_name)
        if not isinstance(node, Agent):
            raise TypeError(f"Coordinator node '{coordinator_name}' resolved to a non-agent type: {type(node).__name__}")

        self._coordinator_agent = node
        return node
