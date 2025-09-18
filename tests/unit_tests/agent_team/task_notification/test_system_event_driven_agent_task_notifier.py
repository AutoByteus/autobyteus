import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call, patch

from autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier import SystemEventDrivenAgentTaskNotifier
from autobyteus.task_management import InMemoryTaskBoard, Task, TaskStatus, FileDeliverable
from autobyteus.agent_team.events import ProcessUserMessageEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.events.event_types import EventType

@pytest.fixture
def mock_team_manager():
    """Provides a mock TeamManager."""
    manager = MagicMock()
    manager.team_id = "test_team_notifier"
    manager.dispatch_user_message_to_agent = AsyncMock()
    return manager

@pytest.fixture
def task_board():
    """Provides a real InMemoryTaskBoard instance that can emit events."""
    return InMemoryTaskBoard(team_id="test_team_notifier")

@pytest.fixture
def single_dependency_tasks() -> list[Task]:
    """Provides a standard list of tasks with a single dependency."""
    tasks = [
        Task(task_name="task_a", assignee_name="AgentA", description="Task A."),
        Task(task_name="task_b", assignee_name="AgentB", description="Task B.", dependencies=["task_a"]),
        Task(task_name="task_c", assignee_name="AgentC", description="Task C."),
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

def test_start_monitoring_subscribes_to_events(notifier: SystemEventDrivenAgentTaskNotifier, task_board: InMemoryTaskBoard):
    """
    Tests that start_monitoring correctly subscribes to the correct events.
    """
    with MagicMock() as mock_subscribe:
        task_board.subscribe = mock_subscribe
        notifier.start_monitoring()

    expected_calls = [
        call(EventType.TASK_BOARD_TASKS_ADDED, notifier._handle_tasks_added),
        call(EventType.TASK_BOARD_STATUS_UPDATED, notifier._handle_status_updated),
    ]
    mock_subscribe.assert_has_calls(expected_calls, any_order=True)
    assert mock_subscribe.call_count == 2

@pytest.mark.asyncio
async def test_notifies_on_tasks_added(notifier, task_board, mock_team_manager, single_dependency_tasks):
    """Tests that initial runnable tasks are dispatched when tasks are added."""
    notifier.start_monitoring()

    task_board.add_tasks(single_dependency_tasks)
    await asyncio.sleep(0.01) # Allow async events to propagate

    assert mock_team_manager.dispatch_user_message_to_agent.call_count == 2
    
    call_args_list = mock_team_manager.dispatch_user_message_to_agent.call_args_list
    dispatched_to = {call.args[0].target_agent_name for call in call_args_list}
    
    assert "AgentA" in dispatched_to
    assert "AgentC" in dispatched_to
    assert "AgentB" not in dispatched_to # B is dependent on A

    for call_arg in call_args_list:
        event = call_arg.args[0]
        assert isinstance(event, ProcessUserMessageEvent)
        assert isinstance(event.user_message, AgentInputUserMessage)
        assert event.user_message.metadata.get('source') == 'system_task_notifier'
        assert "is now ready to start" in event.user_message.content

@pytest.mark.asyncio
@patch("autobyteus.task_management.in_memory_task_board.InMemoryTaskBoard.update_task_status", return_value=True)
async def test_auto_updates_task_status_to_in_progress_on_dispatch(mock_update_status, notifier, task_board, mock_team_manager, single_dependency_tasks):
    """
    Tests that when a task is dispatched, its status is automatically updated to IN_PROGRESS on the board.
    """
    # Arrange
    notifier.start_monitoring()
    
    task_a = next(t for t in single_dependency_tasks if t.task_name == "task_a")
    task_c = next(t for t in single_dependency_tasks if t.task_name == "task_c")

    # Act
    task_board.add_tasks(single_dependency_tasks)
    await asyncio.sleep(0.01) # Allow events to propagate

    # Assert
    # 1. The notifications are still sent correctly
    assert mock_team_manager.dispatch_user_message_to_agent.call_count == 2
    
    # 2. The status update method was called for the two dispatched tasks
    assert mock_update_status.call_count == 2
    
    expected_calls = [
        call(task_id=task_a.task_id, status=TaskStatus.IN_PROGRESS, agent_name="SystemTaskNotifier"),
        call(task_id=task_c.task_id, status=TaskStatus.IN_PROGRESS, agent_name="SystemTaskNotifier"),
    ]
    mock_update_status.assert_has_calls(expected_calls, any_order=True)

@pytest.mark.asyncio
async def test_notifies_when_dependency_completes(notifier, task_board, mock_team_manager, single_dependency_tasks):
    """Tests that a dependent task is notified after its dependency is completed."""
    notifier.start_monitoring()
    task_board.add_tasks(single_dependency_tasks)
    await asyncio.sleep(0.01)
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()

    task_a = next(t for t in single_dependency_tasks if t.task_name == "task_a")

    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    
    assert dispatched_event.target_agent_name == "AgentB"
    assert "deliverables" not in dispatched_event.user_message.content

@pytest.mark.asyncio
async def test_notifies_with_parent_deliverable_context(notifier, task_board, mock_team_manager, single_dependency_tasks):
    """Tests that the notification includes context from a parent task's deliverables."""
    notifier.start_monitoring()
    task_board.add_tasks(single_dependency_tasks)
    await asyncio.sleep(0.01)
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()

    task_a = next(t for t in single_dependency_tasks if t.task_name == "task_a")
    deliverable = FileDeliverable(file_path="./output/a.txt", summary="Generated report A.", author_agent_name="AgentA")
    task_a.file_deliverables.append(deliverable)

    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    
    user_message_content = dispatched_event.user_message.content
    assert "parent task 'task_a' produced the following deliverables:" in user_message_content
    assert "File: ./output/a.txt" in user_message_content
    assert "Summary: Generated report A." in user_message_content

@pytest.mark.asyncio
async def test_notifies_only_when_all_dependencies_are_complete(notifier, task_board, mock_team_manager, multi_dependency_tasks):
    """Tests that a task with multiple dependencies is only notified after all are complete."""
    notifier.start_monitoring()
    task_board.add_tasks(multi_dependency_tasks)
    await asyncio.sleep(0.01)
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()

    task_a = next(t for t in multi_dependency_tasks if t.task_name == "task_a")
    task_b = next(t for t in multi_dependency_tasks if t.task_name == "task_b")
    
    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)
    mock_team_manager.dispatch_user_message_to_agent.assert_not_called()

    task_board.update_task_status(task_b.task_id, TaskStatus.COMPLETED, "AgentB")
    await asyncio.sleep(0.01)
    
    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    assert mock_team_manager.dispatch_user_message_to_agent.call_args.args[0].target_agent_name == "AgentC"

@pytest.mark.asyncio
async def test_does_not_notify_twice(notifier, task_board, mock_team_manager, single_dependency_tasks):
    """Tests that a task is not re-notified if it was already dispatched."""
    notifier.start_monitoring()
    task_board.add_tasks(single_dependency_tasks)
    await asyncio.sleep(0.01)
    
    assert mock_team_manager.dispatch_user_message_to_agent.call_count == 2
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()

    task_c = next(t for t in single_dependency_tasks if t.task_name == "task_c")
    task_board.update_task_status(task_c.task_id, TaskStatus.IN_PROGRESS, "AgentC")
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_user_message_to_agent.assert_not_called()
