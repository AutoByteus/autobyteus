# file: autobyteus/autobyteus/workflow/streaming/agent_event_multiplexer.py
import asyncio
import logging
from typing import TYPE_CHECKING, Dict, Optional

from autobyteus.workflow.streaming.agent_event_bridge import AgentEventBridge

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier
    from autobyteus.workflow.runtime.workflow_worker import WorkflowWorker

logger = logging.getLogger(__name__)

class AgentEventMultiplexer:
    """
    Manages the lifecycle of AgentEventBridge instances for a workflow.
    Its sole responsibility is to create, track, and shut down the bridges
    that forward agent events to the workflow's main event stream.
    """
    def __init__(self, workflow_id: str, notifier: 'WorkflowExternalEventNotifier', worker_ref: 'WorkflowWorker'):
        self._workflow_id = workflow_id
        self._notifier = notifier
        self._worker = worker_ref
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._bridges: Dict[str, AgentEventBridge] = {}
        logger.info(f"AgentEventMultiplexer initialized for workflow '{self._workflow_id}'.")

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Retrieves the event loop from the worker on-demand."""
        if self._loop is None or self._loop.is_closed():
            self._loop = self._worker.get_worker_loop()
            if self._loop is None:
                raise RuntimeError(f"Workflow worker loop for workflow '{self._workflow_id}' is not available or not running.")
        return self._loop

    def start_bridging_agent_events(self, agent: 'Agent', agent_name: str):
        """Creates and starts an AgentEventBridge for a given agent."""
        if agent_name in self._bridges:
            logger.warning(f"Event bridge for agent '{agent_name}' already exists. Skipping creation.")
            return

        try:
            loop = self._get_loop()
        except RuntimeError as e:
            logger.error(f"Cannot create event bridge for '{agent_name}': {e}")
            return

        bridge = AgentEventBridge(
            agent=agent,
            agent_name=agent_name,
            notifier=self._notifier,
            loop=loop
        )
        self._bridges[agent_name] = bridge
        logger.info(f"AgentEventMultiplexer started event bridge for agent '{agent_name}'.")

    async def shutdown(self):
        """Gracefully shuts down all active event bridges."""
        logger.info(f"AgentEventMultiplexer for '{self._workflow_id}' shutting down {len(self._bridges)} event bridges.")
        shutdown_tasks = [bridge.cancel() for bridge in self._bridges.values()]
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        self._bridges.clear()
        logger.info(f"All event bridges for workflow '{self._workflow_id}' have been shut down by multiplexer.")
