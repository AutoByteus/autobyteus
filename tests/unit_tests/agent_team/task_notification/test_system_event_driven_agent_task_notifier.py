import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call

from autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier import SystemEventDrivenAgentTaskNotifier
from autobyteus.task_management import InMemoryTaskBoard, Task, TaskStatus
from autobyteus.agent_team.events import ProcessUserMessageEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.events.event_types import EventType

# --- Mocks and Fixtures ---

@pytest.fixture
def mock_agent_a():
    """Provides a mock agent for AgentA."""
    agent = MagicMock()
    agent.agent_id = "agent_a_id"
    # The agent's context and state no longer need a personal_task_queue
    agent.context = MagicMock()
    agent.context.state = MagicMock()
    return agent

@pytest.fixture
def mock_agent_b():
    """Provides a mock agent for AgentB."""
    agent = MagicMock()
    agent.agent_id = "agent_b_id"
    agent.context = MagicMock()
    agent.context.state = MagicMock()
    return agent

@pytest.fixture
def mock_agent_c():
    """Provides a mock agent for AgentC."""
    agent = MagicMock()
    agent.agent_id = "agent_c_id"
    agent.context = MagicMock()
    agent.context.state = MagicMock()
    return agent

@pytest.fixture
def mock_team_manager(mock_agent_a, mock_agent_b, mock_agent_c):
    """
    Provides a mock TeamManager that can return mock agents by name.
    """
    manager = MagicMock()
    manager.team_id = "test_team_notifier"
    manager.dispatch_user_message_to_agent = AsyncMock()

    # Configure the mock to return the correct agent based on name
    agent_map = {
        "AgentA": mock_agent_a,
        "AgentB": mock_agent_b,
        "AgentC": mock_agent_c,
    }
    
    async def ensure_node_is_ready_side_effect(agent_name):
        return agent_map.get(agent_name)

    manager.ensure_node_is_ready = AsyncMock(side_effect=ensure_node_is_ready_side_effect)
    return manager

@pytest.fixture
def task_board():
    """Provides a real InMemoryTaskBoard instance."""
    return InMemoryTaskBoard(team_id="test_team_notifier")

@pytest.fixture
def single_dependency_tasks() -> list[Task]:
    """Provides a standard list of tasks with a single dependency."""
    tasks = [
        Task(task_name="task_a", assignee_name="AgentA", description="Task A."),
        Task(task_name="task_b", assignee_name="AgentB", description="Task B.", dependencies=["task_a"]),
        Task(task_name="task_c", assignee_name="AgentA", description="Task C."), # Assign to AgentA for batching test
    ]
    name_to_id = {t.task_name: t.task_id for t in tasks}
    for t in tasks:
        t.dependencies = [name_to_id.get(dep) for dep in t.dependencies if dep]
    return tasks

@pytest.fixture
def multi_dependency_tasks() -> list[Task]:
    """Provides tasks where one has multiple dependencies."""
    tasks = [
        Task(task_name="task_a", assignee_name="AgentA", description="Task A."),
        Task(task_name="task_b", assignee_name="AgentB", description="Task B."),
        Task(task_name="task_c", assignee_name="AgentC", description="Task C.", dependencies=["task_a", "task_b"]),
    ]
    name_to_id = {t.task_name: t.task_id for t in tasks}
    for t in tasks:
        t.dependencies = [name_to_id.get(dep) for dep in t.dependencies if dep]
    return tasks

@pytest.fixture
def notifier(task_board, mock_team_manager):
    """Provides an instance of the notifier connected to mocks."""
    return SystemEventDrivenAgentTaskNotifier(task_board=task_board, team_manager=mock_team_manager)

# --- Tests ---

def test_start_monitoring_subscribes_to_events(notifier: SystemEventDrivenAgentTaskNotifier, task_board: InMemoryTaskBoard):
    """Tests that start_monitoring correctly subscribes to the correct events."""
    with MagicMock() as mock_subscribe:
        task_board.subscribe = mock_subscribe
        notifier.start_monitoring()

    expected_calls = [
        call(EventType.TASK_BOARD_TASKS_ADDED, notifier._handle_tasks_changed),
        call(EventType.TASK_BOARD_STATUS_UPDATED, notifier._handle_tasks_changed),
    ]
    mock_subscribe.assert_has_calls(expected_calls, any_order=True)
    assert mock_subscribe.call_count == 2

@pytest.mark.asyncio
async def test_queues_tasks_and_notifies_on_add(notifier, task_board, mock_team_manager, single_dependency_tasks):
    """
    Tests that initial runnable tasks are moved to QUEUED status and a single
    notification is sent to the agent.
    """
    notifier.start_monitoring()
    
    task_a = next(t for t in single_dependency_tasks if t.task_name == "task_a")
    task_c = next(t for t in single_dependency_tasks if t.task_name == "task_c")

    # Act
    task_board.add_tasks(single_dependency_tasks)
    await asyncio.sleep(0.01) # Allow async events to propagate

    # Assert
    # 1. Statuses are updated to QUEUED on the board
    assert task_board.task_statuses[task_a.task_id] == TaskStatus.QUEUED
    assert task_board.task_statuses[task_c.task_id] == TaskStatus.QUEUED
    
    # 2. AgentA was prepared
    mock_team_manager.ensure_node_is_ready.assert_called_once_with("AgentA")

    # 3. AgentA received exactly ONE notification for its TWO tasks
    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    assert isinstance(dispatched_event, ProcessUserMessageEvent)
    assert dispatched_event.target_agent_name == "AgentA"
    assert isinstance(dispatched_event.user_message, AgentInputUserMessage)
    assert "You have new tasks in your queue" in dispatched_event.user_message.content

@pytest.mark.asyncio
async def test_notifies_when_dependency_completes(notifier, task_board, mock_team_manager, single_dependency_tasks):
    """Tests that a dependent task is queued after its dependency is completed."""
    notifier.start_monitoring()
    task_board.add_tasks(single_dependency_tasks)
    await asyncio.sleep(0.01)
    
    # Reset mocks after initial assignment
    mock_team_manager.ensure_node_is_ready.reset_mock()
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()

    task_a = next(t for t in single_dependency_tasks if t.task_name == "task_a")
    task_b = next(t for t in single_dependency_tasks if t.task_name == "task_b")

    # Act: Complete the first task
    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    # Assert
    # 1. Dependent task is now QUEUED
    assert task_board.task_statuses[task_b.task_id] == TaskStatus.QUEUED

    # 2. AgentB was prepared
    mock_team_manager.ensure_node_is_ready.assert_called_once_with("AgentB")
    
    # 3. AgentB received a single notification
    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    assert dispatched_event.target_agent_name == "AgentB"

@pytest.mark.asyncio
async def test_notifies_only_when_all_dependencies_are_complete(notifier, task_board, mock_team_manager, multi_dependency_tasks):
    """Tests that a task with multiple dependencies is only queued after all are complete."""
    notifier.start_monitoring()
    task_board.add_tasks(multi_dependency_tasks)
    await asyncio.sleep(0.01)
    
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()
    mock_team_manager.ensure_node_is_ready.reset_mock()

    task_a = next(t for t in multi_dependency_tasks if t.task_name == "task_a")
    task_b = next(t for t in multi_dependency_tasks if t.task_name == "task_b")
    task_c = next(t for t in multi_dependency_tasks if t.task_name == "task_c")
    
    # Act 1: Complete only the first dependency
    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    # Assert: Nothing should have happened to task_c yet
    mock_team_manager.dispatch_user_message_to_agent.assert_not_called()
    assert task_board.task_statuses[task_c.task_id] == TaskStatus.NOT_STARTED

    # Act 2: Complete the second and final dependency
    task_board.update_task_status(task_b.task_id, TaskStatus.COMPLETED, "AgentB")
    await asyncio.sleep(0.01)
    
    # Assert: Now task_c should be queued and its agent notified
    assert task_board.task_statuses[task_c.task_id] == TaskStatus.QUEUED
    mock_team_manager.ensure_node_is_ready.assert_called_once_with("AgentC")
    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    assert mock_team_manager.dispatch_user_message_to_agent.call_args.args[0].target_agent_name == "AgentC"

@pytest.mark.asyncio
async def test_does_not_re_notify_for_queued_tasks(notifier, task_board, mock_team_manager, single_dependency_tasks):
    """Tests that a task is not re-processed if it's already in the QUEUED state."""
    notifier.start_monitoring()
    task_board.add_tasks(single_dependency_tasks)
    await asyncio.sleep(0.01)
    
    # At this point, task_a and task_c are QUEUED, and AgentA has been notified once.
    assert mock_team_manager.dispatch_user_message_to_agent.call_count == 1
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()

    # Act: Trigger another scan by pretending another task got completed (even one not in the list)
    task_board.emit(EventType.TASK_BOARD_STATUS_UPDATED, payload=MagicMock())
    await asyncio.sleep(0.01)

    # Assert: No new notification was sent because the runnable tasks were already QUEUED.
    mock_team_manager.dispatch_user_message_to_agent.assert_not_called()
