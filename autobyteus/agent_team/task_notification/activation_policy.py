# file: autobyteus/autobyteus/agent_team/task_notification/activation_policy.py
"""
Defines the policy for deciding which agents should be activated based on task runnability.
"""
import logging
from typing import List, Set

from autobyteus.task_management.task import Task

logger = logging.getLogger(__name__)

class ActivationPolicy:
    """
    Encapsulates the "Single Wave" notification logic for an agent team.

    This class maintains a stateful set of agents that have already been
    activated. It decides which new agents should receive a "start work"
    notification based on a list of currently runnable tasks.
    """
    def __init__(self, team_id: str):
        """
        Initializes the ActivationPolicy.

        Args:
            team_id: The ID of the team this policy belongs to, for logging.
        """
        self._team_id = team_id
        self._activated_agents: Set[str] = set()
        logger.debug(f"ActivationPolicy initialized for team '{self._team_id}'.")

    def reset(self):
        """
        Resets the activation state. This should be called when a new batch of
        tasks is published to the task board, signifying a new plan or a
        significant change in scope.
        """
        logger.info(f"Team '{self._team_id}': ActivationPolicy state has been reset. All agents are now considered inactive.")
        self._activated_agents.clear()

    def determine_activations(self, runnable_tasks: List[Task]) -> List[str]:
        """
        Determines which agents should be activated based on a list of runnable tasks.

        An agent is selected for activation if they have one or more runnable tasks
        and have not already been activated in the current work cycle.

        This method is stateful: it updates its internal set of activated agents
        with the new agents it returns.

        Args:
            runnable_tasks: A list of tasks that are currently runnable.

        Returns:
            A list of unique agent names that should be activated.
        """
        if not runnable_tasks:
            return []

        agents_with_runnable_tasks = {task.assignee_name for task in runnable_tasks}
        
        # Determine which of these agents have not yet been activated.
        new_agents_to_activate = list(agents_with_runnable_tasks - self._activated_agents)

        if new_agents_to_activate:
            # Update the state to remember that these agents have now been activated.
            self._activated_agents.update(new_agents_to_activate)
            logger.info(f"Team '{self._team_id}': Policy determined {len(new_agents_to_activate)} new agent(s) to activate: {new_agents_to_activate}. "
                        f"Total activated agents is now {len(self._activated_agents)}.")
        
        return new_agents_to_activate
