# file: autobyteus/autobyteus/workflow/streaming/agent_event_multiplexer.py
import asyncio
import logging
from typing import TYPE_CHECKING, Dict, Optional

from autobyteus.workflow.streaming.agent_event_bridge import AgentEventBridge
from autobyteus.workflow.streaming.workflow_event_bridge import WorkflowEventBridge

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.workflow.agentic_workflow import AgenticWorkflow
    from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier
    from autobyteus.workflow.runtime.workflow_worker import WorkflowWorker

logger = logging.getLogger(__name__)

class AgentEventMultiplexer:
    """
    Manages the lifecycle of event bridges for all nodes (agents and sub-workflows).
    It creates, tracks, and shuts down the bridges that forward node events
    to the workflow's main event stream.
    """
    def __init__(self, workflow_id: str, notifier: 'WorkflowExternalEventNotifier', worker_ref: 'WorkflowWorker'):
        self._workflow_id = workflow_id
        self._notifier = notifier
        self._worker = worker_ref
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._agent_bridges: Dict[str, AgentEventBridge] = {}
        self._workflow_bridges: Dict[str, WorkflowEventBridge] = {}
        logger.info(f"AgentEventMultiplexer initialized for workflow '{self._workflow_id}'.")

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Retrieves the event loop from the worker on-demand."""
        if self._loop is None or self._loop.is_closed():
            self._loop = self._worker.get_worker_loop()
            if self._loop is None:
                raise RuntimeError(f"Workflow worker loop for workflow '{self._workflow_id}' is not available or not running.")
        return self._loop

    def start_bridging_agent_events(self, agent: 'Agent', agent_name: str):
        """Creates and starts an AgentEventBridge for a direct agent node."""
        if agent_name in self._agent_bridges:
            logger.warning(f"Event bridge for agent '{agent_name}' already exists. Skipping creation.")
            return

        bridge = AgentEventBridge(agent=agent, agent_name=agent_name, notifier=self._notifier, loop=self._get_loop())
        self._agent_bridges[agent_name] = bridge
        logger.info(f"AgentEventMultiplexer started agent event bridge for '{agent_name}'.")

    def start_bridging_workflow_events(self, sub_workflow: 'AgenticWorkflow', node_name: str):
        """Creates and starts a WorkflowEventBridge for a sub-workflow node."""
        if node_name in self._workflow_bridges:
            logger.warning(f"Event bridge for sub-workflow '{node_name}' already exists. Skipping creation.")
            return
            
        bridge = WorkflowEventBridge(sub_workflow=sub_workflow, sub_workflow_node_name=node_name, parent_notifier=self._notifier, loop=self._get_loop())
        self._workflow_bridges[node_name] = bridge
        logger.info(f"AgentEventMultiplexer started workflow event bridge for '{node_name}'.")

    async def shutdown(self):
        """Gracefully shuts down all active event bridges."""
        logger.info(f"AgentEventMultiplexer for '{self._workflow_id}' shutting down all event bridges.")
        agent_bridge_tasks = [b.cancel() for b in self._agent_bridges.values()]
        workflow_bridge_tasks = [b.cancel() for b in self._workflow_bridges.values()]
        
        await asyncio.gather(*(agent_bridge_tasks + workflow_bridge_tasks), return_exceptions=True)
        
        self._agent_bridges.clear()
        self._workflow_bridges.clear()
        logger.info(f"All event bridges for workflow '{self._workflow_id}' have been shut down by multiplexer.")
