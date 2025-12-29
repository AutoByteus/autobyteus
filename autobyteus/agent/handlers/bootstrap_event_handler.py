# file: autobyteus/autobyteus/agent/handlers/bootstrap_event_handler.py
import logging
from typing import List, Optional, TYPE_CHECKING

from autobyteus.agent.bootstrap_steps.agent_bootstrapper import AgentBootstrapper
from autobyteus.agent.bootstrap_steps.base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.events import (
    AgentErrorEvent,
    AgentReadyEvent,
    BootstrapStartedEvent,
    BootstrapStepRequestedEvent,
    BootstrapStepCompletedEvent,
    BootstrapCompletedEvent,
)
from autobyteus.agent.handlers.base_event_handler import AgentEventHandler

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

_BOOTSTRAP_STEPS_KEY = "_bootstrap_steps"


class BootstrapEventHandler(AgentEventHandler):
    """
    Orchestrates the agent bootstrap sequence using internal lifecycle events.
    """

    def __init__(self, steps: Optional[List[BaseBootstrapStep]] = None) -> None:
        self._bootstrapper = AgentBootstrapper(steps=steps)

    async def handle(self, event: object, context: 'AgentContext') -> None:
        if isinstance(event, BootstrapStartedEvent):
            await self._handle_bootstrap_started(context)
            return

        if isinstance(event, BootstrapStepRequestedEvent):
            await self._handle_bootstrap_step_requested(event, context)
            return

        if isinstance(event, BootstrapStepCompletedEvent):
            await self._handle_bootstrap_step_completed(event, context)
            return

        if isinstance(event, BootstrapCompletedEvent):
            await self._handle_bootstrap_completed(event, context)
            return

        logger.warning(f"BootstrapEventHandler received unexpected event type: {type(event).__name__}")

    async def _handle_bootstrap_started(self, context: 'AgentContext') -> None:
        steps = list(self._bootstrapper.bootstrap_steps)
        context.state.custom_data[_BOOTSTRAP_STEPS_KEY] = steps

        if not steps:
            logger.info(f"Agent '{context.agent_id}': No bootstrap steps configured. Marking bootstrap complete.")
            await context.input_event_queues.enqueue_internal_system_event(
                BootstrapCompletedEvent(success=True)
            )
            return

        logger.info(f"Agent '{context.agent_id}': Bootstrap started with {len(steps)} steps.")
        await context.input_event_queues.enqueue_internal_system_event(
            BootstrapStepRequestedEvent(step_index=0)
        )

    async def _handle_bootstrap_step_requested(self, event: BootstrapStepRequestedEvent, context: 'AgentContext') -> None:
        steps: Optional[List[BaseBootstrapStep]] = context.state.custom_data.get(_BOOTSTRAP_STEPS_KEY)
        if not steps:
            error_message = "Bootstrap steps list missing from context during step request."
            logger.error(f"Agent '{context.agent_id}': {error_message}")
            await self._notify_bootstrap_error(context, error_message)
            await context.input_event_queues.enqueue_internal_system_event(
                BootstrapCompletedEvent(success=False, error_message=error_message)
            )
            return

        step_index = event.step_index
        if step_index < 0 or step_index >= len(steps):
            error_message = f"Invalid bootstrap step index {step_index}."
            logger.error(f"Agent '{context.agent_id}': {error_message}")
            await self._notify_bootstrap_error(context, error_message)
            await context.input_event_queues.enqueue_internal_system_event(
                BootstrapCompletedEvent(success=False, error_message=error_message)
            )
            return

        step = steps[step_index]
        step_name = step.__class__.__name__
        logger.debug(f"Agent '{context.agent_id}': Executing bootstrap step {step_index + 1}/{len(steps)}: {step_name}")

        try:
            success = await step.execute(context)
        except Exception as e:  # pragma: no cover
            error_message = f"Exception during bootstrap step '{step_name}': {e}"
            logger.error(f"Agent '{context.agent_id}': {error_message}", exc_info=True)
            success = False
        if not success:
            error_message = f"Bootstrap step '{step_name}' failed."
            await self._notify_bootstrap_error(context, error_message)

        await context.input_event_queues.enqueue_internal_system_event(
            BootstrapStepCompletedEvent(
                step_index=step_index,
                step_name=step_name,
                success=success,
                error_message=None if success else f"Step '{step_name}' failed",
            )
        )

    async def _handle_bootstrap_step_completed(self, event: BootstrapStepCompletedEvent, context: 'AgentContext') -> None:
        if not event.success:
            await context.input_event_queues.enqueue_internal_system_event(
                BootstrapCompletedEvent(success=False, error_message=event.error_message)
            )
            return

        steps: Optional[List[BaseBootstrapStep]] = context.state.custom_data.get(_BOOTSTRAP_STEPS_KEY)
        if not steps:
            error_message = "Bootstrap steps list missing during step completion."
            logger.error(f"Agent '{context.agent_id}': {error_message}")
            await self._notify_bootstrap_error(context, error_message)
            await context.input_event_queues.enqueue_internal_system_event(
                BootstrapCompletedEvent(success=False, error_message=error_message)
            )
            return

        next_index = event.step_index + 1
        if next_index < len(steps):
            await context.input_event_queues.enqueue_internal_system_event(
                BootstrapStepRequestedEvent(step_index=next_index)
            )
            return

        await context.input_event_queues.enqueue_internal_system_event(
            BootstrapCompletedEvent(success=True)
        )

    async def _handle_bootstrap_completed(self, event: BootstrapCompletedEvent, context: 'AgentContext') -> None:
        if not event.success:
            logger.error(
                f"Agent '{context.agent_id}': Bootstrap completed with failure. "
                f"Error: {event.error_message}"
            )
            await self._notify_bootstrap_error(context, event.error_message or "Bootstrap failed.")
            return

        logger.info(f"Agent '{context.agent_id}': Bootstrap completed successfully. Emitting AgentReadyEvent.")
        await context.input_event_queues.enqueue_internal_system_event(AgentReadyEvent())

    async def _notify_bootstrap_error(self, context: 'AgentContext', error_message: str) -> None:
        await context.input_event_queues.enqueue_internal_system_event(
            AgentErrorEvent(error_message=error_message, exception_details=error_message)
        )
