# file: autobyteus/autobyteus/agent_team/bootstrap_steps/agent_tool_injection_step.py
import logging
from typing import TYPE_CHECKING, Dict, Set

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.agent_team.context.team_node_config import TeamNodeConfig
from autobyteus.tools.registry import default_tool_registry

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class AgentToolInjectionStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to inject team-aware tools like SendMessageTo into
    agent configurations just before they are used. This step is now effectively
    a placeholder as tool injection is handled just-in-time by the TeamManager,
    but it is kept for potential future use and to maintain the bootstrap sequence structure.
    The primary logic of applying the coordinator prompt has been moved to the TeamManager
    to ensure it happens just before the coordinator is created.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing AgentToolInjectionStep (now a placeholder).")
        # The logic for injecting SendMessageTo and setting the coordinator prompt is now
        # handled just-in-time by the TeamManager to better support lazy-loading of nodes.
        # This step is preserved in the bootstrap sequence for clarity and future expansion.
        logger.debug(f"Team '{team_id}': Tool injection and prompt setting are deferred to TeamManager.")
        return True
