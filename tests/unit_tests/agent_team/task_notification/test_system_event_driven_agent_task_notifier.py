# file: autobyteus/tests/unit_tests/agent_team/task_notification/test_system_event_driven_agent_task_notifier.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call, patch

# We are testing the orchestrator, so we mock its direct dependencies
from autobyteus.agent_team.task_notification.activation_policy import ActivationPolicy
from autobyteus.agent_team.task_notification.task_activator import TaskActivator

from autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier import SystemEventDrivenAgentTaskNotifier
from autobyteus.task_management import InMemoryTaskPlan, TaskDefinitionSchema, TaskStatus
from autobyteus.events.event_types import EventType
from autobyteus.task_management.events import TasksCreatedEvent, TaskStatusUpdatedEvent

# --- Mocks and Fixtures ---

@pytest.fixture
def mock_policy():
    """Provides a mock ActivationPolicy."""
    policy = MagicMock(spec=ActivationPolicy)
    policy.reset = MagicMock()
    policy.determine_activations = MagicMock(return_value=[])
    return policy

@pytest.fixture
def mock_activator():
    """Provides a mock TaskActivator."""
    activator = MagicMock(spec=TaskActivator)
    activator.activate_agent = AsyncMock()
    return activator

@pytest.fixture
def task_plan():
    """Provides a real InMemoryTaskPlan instance for realistic state changes."""
    return InMemoryTaskPlan(team_id="test_orchestrator_team")

@pytest.fixture
def notifier(task_plan, mock_policy, mock_activator):
    """
    Provides an instance of the notifier with its dependencies mocked out.
    We patch the __init__ to inject our mocks.
    """
    with patch('autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier.ActivationPolicy', return_value=mock_policy), \
         patch('autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier.TaskActivator', return_value=mock_activator):
        
        # The team_manager is now only passed to the activator, so we can use a simple mock here.
        mock_team_manager = MagicMock()
        mock_team_manager.team_id = "test_orchestrator_team"
        
        notifier_instance = SystemEventDrivenAgentTaskNotifier(task_plan=task_plan, team_manager=mock_team_manager)
        yield notifier_instance

@pytest.fixture
def tasks():
    """Provides a standard list of task definitions."""
    task_list = [
        TaskDefinitionSchema(task_name="task_a", assignee_name="AgentA", description="Task A."),
        TaskDefinitionSchema(task_name="task_b", assignee_name="AgentB", description="Task B.", dependencies=["task_a"]),
    ]
    return task_list

# --- Tests ---

@pytest.mark.asyncio
async def test_on_tasks_created_resets_policy_and_activates(notifier, task_plan, mock_policy, mock_activator, tasks):
    """
    Tests that on TasksCreatedEvent, the orchestrator resets the policy, gets a
    decision, updates task statuses, and calls the activator.
    """
    created_tasks = task_plan.add_tasks(tasks)
    task_a = created_tasks[0]
    
    # Configure mock policy to return an agent to activate
    mock_policy.determine_activations.return_value = ["AgentA"]
    
    # Act
    # The handler is being tested in isolation. We must first establish the state
    # of the task plan that the handler will read from. The TasksCreatedEvent itself
    # just carries data; it doesn't mutate the board's state.
    event = TasksCreatedEvent(team_id=task_plan.team_id, tasks=created_tasks)
    await notifier._handle_tasks_changed(event)
    
    # Assert Orchestration Flow
    # 1. Policy was reset because it's a TasksCreatedEvent
    mock_policy.reset.assert_called_once()
    
    # 2. Policy was asked for a decision
    mock_policy.determine_activations.assert_called_once()
    
    # 3. Task status was updated on the board for the runnable task
    assert task_plan.task_statuses[task_a.task_id] == TaskStatus.QUEUED
    
    # 4. Activator was called for the agent returned by the policy
    mock_activator.activate_agent.assert_awaited_once_with("AgentA")

@pytest.mark.asyncio
async def test_on_status_update_does_not_reset_policy(notifier, task_plan, mock_policy, mock_activator, tasks):
    """
    Tests that on TaskStatusUpdatedEvent, the orchestrator does NOT reset the
    policy, but still orchestrates the activation for any handoffs.
    """
    created_tasks = task_plan.add_tasks(tasks)
    task_b = created_tasks[1]
    
    # Configure mock policy to decide AgentB is ready for a handoff
    mock_policy.determine_activations.return_value = ["AgentB"]

    # Act
    event = TaskStatusUpdatedEvent(team_id=task_plan.team_id, task_id="any_id", new_status=TaskStatus.COMPLETED, agent_name="AgentA")
    # Manually set up the board state to make task_b runnable for the test
    task_plan.update_task_status(created_tasks[0].task_id, TaskStatus.COMPLETED, "AgentA")

    await notifier._handle_tasks_changed(event)
    
    # Assert Orchestration Flow
    # 1. Policy was NOT reset
    mock_policy.reset.assert_not_called()
    
    # 2. Policy was asked for a decision
    mock_policy.determine_activations.assert_called_once()
    
    # 3. Task status was updated
    assert task_plan.task_statuses[task_b.task_id] == TaskStatus.QUEUED
    
    # 4. Activator was called for the handoff
    mock_activator.activate_agent.assert_awaited_once_with("AgentB")

@pytest.mark.asyncio
async def test_does_not_activate_if_policy_returns_empty(notifier, task_plan, mock_policy, mock_activator, tasks):
    """
    Tests that the activator is not called if the policy determines no new agents
    should be activated, even if there are runnable tasks.
    """
    # Configure mock policy to return an empty list (no one to activate)
    mock_policy.determine_activations.return_value = []
    
    # Act
    event = TaskStatusUpdatedEvent(team_id=task_plan.team_id, task_id="any_id", new_status=TaskStatus.COMPLETED, agent_name="AgentA")
    created_tasks = task_plan.add_tasks(tasks)
    task_plan.update_task_status(created_tasks[0].task_id, TaskStatus.COMPLETED, "AgentA")

    await notifier._handle_tasks_changed(event)
    
    # Assert Orchestration Flow
    # 1. Policy was asked for a decision
    mock_policy.determine_activations.assert_called_once()
    
    # 2. Activator was NOT called
    mock_activator.activate_agent.assert_not_awaited()

    # 3. Task statuses are NOT updated to QUEUED by the orchestrator in this case.
    # The orchestrator only queues tasks for agents it is about to activate.
    assert task_plan.task_statuses[created_tasks[1].task_id] == TaskStatus.NOT_STARTED
