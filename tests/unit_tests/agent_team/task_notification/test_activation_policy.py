# file: autobyteus/tests/unit_tests/agent_team/task_notification/test_activation_policy.py
"""
Unit tests for the ActivationPolicy class.
"""
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.task_notification.activation_policy import ActivationPolicy
from autobyteus.task_management.task import Task

@pytest.fixture
def policy():
    """Provides a fresh ActivationPolicy instance for each test."""
    return ActivationPolicy(team_id="test_policy_team")

def create_mock_task(assignee: str) -> Task:
    """Helper to create a mock task with a specific assignee."""
    task = MagicMock(spec=Task)
    task.assignee_name = assignee
    return task

def test_initialization(policy: ActivationPolicy):
    """Tests that the policy initializes with an empty set of activated agents."""
    assert policy._activated_agents == set()

def test_determine_activations_initial_call(policy: ActivationPolicy):
    """
    Tests that an initial call with runnable tasks for two new agents returns
    both agents and adds them to the internal state.
    """
    runnable_tasks = [create_mock_task("AgentA"), create_mock_task("AgentB"), create_mock_task("AgentA")]
    
    activations = policy.determine_activations(runnable_tasks)
    
    assert sorted(activations) == ["AgentA", "AgentB"]
    assert policy._activated_agents == {"AgentA", "AgentB"}

def test_determine_activations_no_new_agents(policy: ActivationPolicy):
    """
    Tests that a subsequent call with tasks for already-activated agents
    returns an empty list.
    """
    # Prime the state
    policy._activated_agents = {"AgentA", "AgentB"}
    
    runnable_tasks = [create_mock_task("AgentA"), create_mock_task("AgentB")]
    
    activations = policy.determine_activations(runnable_tasks)
    
    assert activations == []
    assert policy._activated_agents == {"AgentA", "AgentB"} # State should be unchanged

def test_determine_activations_handoff(policy: ActivationPolicy):
    """
    Tests that a subsequent call with a task for a new agent (a handoff)
    returns only the new agent's name.
    """
    # Prime the state
    policy._activated_agents = {"AgentA"}
    
    runnable_tasks = [create_mock_task("AgentB")]
    
    activations = policy.determine_activations(runnable_tasks)
    
    assert activations == ["AgentB"]
    assert policy._activated_agents == {"AgentA", "AgentB"} # State should be updated

def test_determine_activations_mixed_batch(policy: ActivationPolicy):
    """
    Tests a call with tasks for both an already-activated agent and a new agent.
    """
    # Prime the state
    policy._activated_agents = {"AgentA"}
    
    runnable_tasks = [create_mock_task("AgentA"), create_mock_task("AgentB")]
    
    activations = policy.determine_activations(runnable_tasks)
    
    assert activations == ["AgentB"]
    assert policy._activated_agents == {"AgentA", "AgentB"}

def test_reset(policy: ActivationPolicy):
    """Tests that the reset method clears the internal state."""
    # Prime the state
    policy._activated_agents = {"AgentA", "AgentB"}
    
    policy.reset()
    
    assert policy._activated_agents == set()

def test_determine_activations_after_reset(policy: ActivationPolicy):
    """
    Tests that after a reset, the policy behaves as if it's the initial call.
    """
    # Prime and reset
    policy._activated_agents = {"AgentA"}
    policy.reset()
    
    runnable_tasks = [create_mock_task("AgentA")]
    
    activations = policy.determine_activations(runnable_tasks)
    
    assert activations == ["AgentA"]
    assert policy._activated_agents == {"AgentA"}

def test_determine_activations_empty_input(policy: ActivationPolicy):
    """Tests that an empty list of tasks results in an empty list of activations."""
    activations = policy.determine_activations([])
    
    assert activations == []
    assert policy._activated_agents == set()
