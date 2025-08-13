# file: autobyteus/tests/unit_tests/agent_team/task_notification/test_system_event_driven_agent_task_notifier.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call

from autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier import SystemEventDrivenAgentTaskNotifier
from autobyteus.task_management import InMemoryTaskBoard, Task, TaskPlan, TaskStatus, FileDeliverable
from autobyteus.agent_team.events import InterAgentMessageRequestEvent
from autobyteus.events.event_types import EventType

@pytest.fixture
def mock_team_manager():
    """Provides a mock TeamManager."""
    manager = MagicMock()
    manager.team_id = "test_team_notifier"
    manager.dispatch_inter_agent_message_request = AsyncMock()
    return manager

@pytest.fixture
def task_board():
    """Provides a real InMemoryTaskBoard instance that can emit events."""
    return InMemoryTaskBoard(team_id="test_team_notifier")

@pytest.fixture
def single_dependency_plan():
    """Provides a standard task plan with a single dependency."""
    plan = TaskPlan(
        overall_goal="Test the notifier.",
        tasks=[
            Task(task_name="task_a", assignee_name="AgentA", description="Task A."),
            Task(task_name="task_b", assignee_name="AgentB", description="Task B.", dependencies=["task_a"]),
            Task(task_name="task_c", assignee_name="AgentC", description="Task C."),
        ]
    )
    plan.hydrate_dependencies()
    return plan

@pytest.fixture
def multi_dependency_plan():
    """Provides a task plan with a task that has multiple dependencies."""
    plan = TaskPlan(
        overall_goal="Test multi-dependency notification.",
        tasks=[
            Task(task_name="task_a", assignee_name="AgentA", description="Task A."),
            Task(task_name="task_b", assignee_name="AgentB", description="Task B."),
            Task(task_name="task_c", assignee_name="AgentC", description="Task C.", dependencies=["task_a", "task_b"]),
        ]
    )
    plan.hydrate_dependencies()
    return plan

@pytest.fixture
def notifier(task_board, mock_team_manager):
    """Provides an instance of the notifier connected to mocks."""
    return SystemEventDrivenAgentTaskNotifier(task_board=task_board, team_manager=mock_team_manager)

def test_start_monitoring_subscribes_to_events(notifier: SystemEventDrivenAgentTaskNotifier, task_board: InMemoryTaskBoard):
    """
    Tests that start_monitoring correctly calls the 'subscribe' method on the task board.
    """
    mock_subscribe_method = MagicMock()
    task_board.subscribe = mock_subscribe_method

    notifier.start_monitoring()

    expected_calls = [
        call(EventType.TASK_BOARD_PLAN_PUBLISHED, notifier._handle_task_board_update),
        call(EventType.TASK_BOARD_STATUS_UPDATED, notifier._handle_task_board_update),
    ]
    mock_subscribe_method.assert_has_calls(expected_calls, any_order=True)
    assert mock_subscribe_method.call_count == 2

@pytest.mark.asyncio
async def test_notifies_on_plan_published(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that initial runnable tasks are dispatched when a plan is published."""
    notifier.start_monitoring()

    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)

    assert mock_team_manager.dispatch_inter_agent_message_request.call_count == 2
    
    call_args_list = mock_team_manager.dispatch_inter_agent_message_request.call_args_list
    dispatched_to = {call.args[0].recipient_name for call in call_args_list}
    assert "AgentA" in dispatched_to
    assert "AgentC" in dispatched_to
    assert "AgentB" not in dispatched_to

@pytest.mark.asyncio
async def test_notifies_when_dependency_completes_without_deliverables(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that a dependent task is notified after its dependency is completed, checking content."""
    notifier.start_monitoring()
    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)
    mock_team_manager.dispatch_inter_agent_message_request.reset_mock()

    task_a = next(t for t in single_dependency_plan.tasks if t.task_name == "task_a")

    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_inter_agent_message_request.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_inter_agent_message_request.call_args.args[0]
    assert dispatched_event.recipient_name == "AgentB"
    assert "Your task 'task_b' is now ready to start." in dispatched_event.content
    assert "Your task description:\nTask B." in dispatched_event.content
    assert "deliverables" not in dispatched_event.content  # Explicitly check that this is not present

@pytest.mark.asyncio
async def test_notifies_with_parent_deliverable_context(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that the notification includes context from a parent task's deliverables."""
    notifier.start_monitoring()
    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)
    mock_team_manager.dispatch_inter_agent_message_request.reset_mock()

    task_a = next(t for t in single_dependency_plan.tasks if t.task_name == "task_a")
    # Manually add a deliverable to the parent task before completing it
    deliverable = FileDeliverable(file_path="./output/a.txt", summary="Generated report A.", author_agent_name="AgentA")
    task_a.file_deliverables.append(deliverable)

    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_inter_agent_message_request.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_inter_agent_message_request.call_args.args[0]
    assert dispatched_event.recipient_name == "AgentB"
    # Assert that all parts of the context-rich message are present
    assert "Your task is now unblocked." in dispatched_event.content
    assert "context from the completed parent task(s):" in dispatched_event.content
    assert "parent task 'task_a' produced the following deliverables:" in dispatched_event.content
    assert "File: ./output/a.txt" in dispatched_event.content
    assert "Summary: Generated report A." in dispatched_event.content
    assert "Your task description:\nTask B." in dispatched_event.content

@pytest.mark.asyncio
async def test_notifies_only_when_all_dependencies_are_complete(notifier, task_board, mock_team_manager, multi_dependency_plan):
    """Tests that a task with multiple dependencies is only notified after all are complete."""
    notifier.start_monitoring()
    task_board.load_task_plan(multi_dependency_plan)
    await asyncio.sleep(0.01) # task_a and task_b should not be dispatched, only tasks without deps (none in this plan)
    mock_team_manager.dispatch_inter_agent_message_request.reset_mock()

    task_a = next(t for t in multi_dependency_plan.tasks if t.task_name == "task_a")
    task_b = next(t for t in multi_dependency_plan.tasks if t.task_name == "task_b")
    
    # Complete task_a, which is only one of the two dependencies for task_c
    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    # Assert that task_c has NOT been notified yet
    mock_team_manager.dispatch_inter_agent_message_request.assert_not_called()

    # Now complete task_b, the final dependency
    task_board.update_task_status(task_b.task_id, TaskStatus.COMPLETED, "AgentB")
    await asyncio.sleep(0.01)
    
    # Assert that task_c has NOW been notified
    mock_team_manager.dispatch_inter_agent_message_request.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_inter_agent_message_request.call_args.args[0]
    assert dispatched_event.recipient_name == "AgentC"

@pytest.mark.asyncio
async def test_does_not_notify_twice(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that a task is not re-notified if it was already dispatched."""
    notifier.start_monitoring()
    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)
    assert mock_team_manager.dispatch_inter_agent_message_request.call_count == 2
    mock_team_manager.dispatch_inter_agent_message_request.reset_mock()

    task_c = next(t for t in single_dependency_plan.tasks if t.task_name == "task_c")
    task_board.update_task_status(task_c.task_id, TaskStatus.IN_PROGRESS, "AgentC")
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_inter_agent_message_request.assert_not_called()

@pytest.mark.asyncio
async def test_resets_on_new_plan(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that dispatched state is cleared when a new plan is loaded."""
    notifier.start_monitoring()
    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)
    assert mock_team_manager.dispatch_inter_agent_message_request.call_count == 2

    mock_team_manager.dispatch_inter_agent_message_request.reset_mock()
    new_plan = TaskPlan(overall_goal="New Goal", tasks=[Task(task_name="new_task", assignee_name="NewAgent", description="desc")])
    task_board.load_task_plan(new_plan)
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_inter_agent_message_request.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_inter_agent_message_request.call_args.args[0]
    assert dispatched_event.recipient_name == "NewAgent"
