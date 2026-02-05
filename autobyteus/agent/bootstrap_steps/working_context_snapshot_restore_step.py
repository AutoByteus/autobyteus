import logging
from typing import TYPE_CHECKING

from .base_bootstrap_step import BaseBootstrapStep
from autobyteus.memory.restore.working_context_snapshot_bootstrapper import WorkingContextSnapshotBootstrapper

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


class WorkingContextSnapshotRestoreStep(BaseBootstrapStep):
    def __init__(self, bootstrapper: WorkingContextSnapshotBootstrapper | None = None) -> None:
        self._bootstrapper = bootstrapper or WorkingContextSnapshotBootstrapper()
        logger.debug("WorkingContextSnapshotRestoreStep initialized.")

    async def execute(self, context: "AgentContext") -> bool:
        restore_options = getattr(context.state, "restore_options", None)
        if not restore_options:
            return True

        memory_manager = getattr(context.state, "memory_manager", None)
        if not memory_manager:
            logger.error("WorkingContextSnapshotRestoreStep requires a memory manager to restore working context snapshot.")
            return False

        system_prompt = context.state.processed_system_prompt
        if not system_prompt:
            llm_instance = context.llm_instance
            system_prompt = llm_instance.config.system_message if llm_instance else ""

        try:
            self._bootstrapper.bootstrap(memory_manager, system_prompt, restore_options)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("WorkingContextSnapshotRestoreStep failed: %s", exc, exc_info=True)
            return False
