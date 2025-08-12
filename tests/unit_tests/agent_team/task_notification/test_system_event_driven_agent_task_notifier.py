# file: autobyteus/tests/unit_tests/agent_team/task_notification/test_system_event_driven_agent_task_notifier.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call

from autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier import SystemEventDrivenAgentTaskNotifier
from autobyteus.task_management import InMemoryTaskBoard, Task, TaskPlan, TaskStatus
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
def task_plan():
    """Provides a standard task plan with dependencies."""
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
def notifier(task_board, mock_team_manager):
    """Provides an instance of the notifier connected to mocks."""
    return SystemEventDrivenAgentTaskNotifier(task_board=task_board, team_manager=mock_team_manager)

def test_start_monitoring_subscribes_to_events(notifier: SystemEventDrivenAgentTaskNotifier, task_board: InMemoryTaskBoard):
    """
    Tests that start_monitoring correctly calls the 'subscribe' method on the task board.
    This test verifies the interaction behavior rather than inspecting internal state.
    """
    # Arrange
    # Replace the real subscribe method with a mock to spy on calls to it.
    mock_subscribe_method = MagicMock()
    task_board.subscribe = mock_subscribe_method

    # Act
    notifier.start_monitoring()

    # Assert
    # Verify that the subscribe method was called with the expected arguments.
    expected_calls = [
        call(EventType.TASK_BOARD_PLAN_PUBLISHED, notifier._handle_task_board_update),
        call(EventType.TASK_BOARD_STATUS_UPDATED, notifier._handle_task_board_update),
    ]
    mock_subscribe_method.assert_has_calls(expected_calls, any_order=True)
    assert mock_subscribe_method.call_count == 2

@pytest.mark.asyncio
async def test_notifies_on_plan_published(notifier, task_board, mock_team_manager, task_plan):
    """Tests that initial runnable tasks are dispatched when a plan is published."""
    # Arrange
    notifier.start_monitoring()

    # Act
    task_board.load_task_plan(task_plan) # This emits the PLAN_PUBLISHED event

    # Allow event to be processed
    await asyncio.sleep(0.01)

    # Assert
    # Should have called for task_a and task_c, but not task_b
    assert mock_team_manager.dispatch_inter_agent_message_request.call_count == 2
    
    call_args_list = mock_team_manager.dispatch_inter_agent_message_request.call_args_list
    dispatched_to = {call.args[0].recipient_name for call in call_args_list}
    assert "AgentA" in dispatched_to
    assert "AgentC" in dispatched_to
    assert "AgentB" not in dispatched_to

@pytest.mark.asyncio
async def test_notifies_on_status_update_unblocks_task(notifier, task_board, mock_team_manager, task_plan):
    """Tests that a dependent task is notified after its dependency is completed."""
    # Arrange
    notifier.start_monitoring()
    task_board.load_task_plan(task_plan)
    await asyncio.sleep(0.01) # Process initial notifications
    mock_team_manager.dispatch_inter_agent_message_request.reset_mock()

    task_a = next(t for t in task_plan.tasks if t.task_name == "task_a")

    # Act
    # Complete task_a, which should unblock task_b
    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01) # Process status update event

    # Assert
    mock_team_manager.dispatch_inter_agent_message_request.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_inter_agent_message_request.call_args.args[0]
    assert isinstance(dispatched_event, InterAgentMessageRequestEvent)
    assert dispatched_event.recipient_name == "AgentB"
    assert "Task B" in dispatched_event.content

@pytest.mark.asyncio
async def test_does_not_notify_twice(notifier, task_board, mock_team_manager, task_plan):
    """Tests that a task is not re-notified if it was already dispatched."""
    # Arrange
    notifier.start_monitoring()
    task_board.load_task_plan(task_plan)
    await asyncio.sleep(0.01) # Process initial notifications
    assert mock_team_manager.dispatch_inter_agent_message_request.call_count == 2
    mock_team_manager.dispatch_inter_agent_message_request.reset_mock()

    # Act
    # Trigger another update that doesn't change what's runnable
    task_c = next(t for t in task_plan.tasks if t.task_name == "task_c")
    task_board.update_task_status(task_c.task_id, TaskStatus.IN_PROGRESS, "AgentC")
    await asyncio.sleep(0.01)

    # Assert
    mock_team_manager.dispatch_inter_agent_message_request.assert_not_called()

@pytest.mark.asyncio
async def test_resets_on_new_plan(notifier, task_board, mock_team_manager, task_plan):
    """Tests that dispatched state is cleared when a new plan is loaded."""
    # Arrange
    notifier.start_monitoring()
    task_board.load_task_plan(task_plan)
    await asyncio.sleep(0.01) # Process first plan
    assert mock_team_manager.dispatch_inter_agent_message_request.call_count == 2

    # Act
    # Load a second, identical plan
    mock_team_manager.dispatch_inter_agent_message_request.reset_mock()
    new_plan = TaskPlan(overall_goal="New Goal", tasks=[Task(task_name="new_task", assignee_name="NewAgent", description="desc")])
    task_board.load_task_plan(new_plan)
    await asyncio.sleep(0.01)

    # Assert
    # It should have dispatched the new task
    mock_team_manager.dispatch_inter_agent_message_request.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_inter_agent_message_request.call_args.args[0]
    assert dispatched_event.recipient_name == "NewAgent"
