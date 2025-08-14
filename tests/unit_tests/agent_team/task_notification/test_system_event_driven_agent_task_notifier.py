import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, call

from autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier import SystemEventDrivenAgentTaskNotifier
from autobyteus.task_management import InMemoryTaskBoard, Task, TaskPlan, TaskStatus, FileDeliverable
from autobyteus.agent_team.events import ProcessUserMessageEvent # Changed from InterAgentMessageRequestEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage # Added for the new message type
from autobyteus.events.event_types import EventType

@pytest.fixture
def mock_team_manager():
    """Provides a mock TeamManager."""
    manager = MagicMock()
    manager.team_id = "test_team_notifier"
    manager.dispatch_user_message_to_agent = AsyncMock() # Changed to the new dispatch method
    # Ensure the old method is not called, though it shouldn't be by the notifier anymore
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
    await asyncio.sleep(0.01) # Allow async calls to propagate

    # Now we expect dispatch_user_message_to_agent to be called twice
    assert mock_team_manager.dispatch_user_message_to_agent.call_count == 2
    
    call_args_list = mock_team_manager.dispatch_user_message_to_agent.call_args_list
    
    # Extract recipient names from the ProcessUserMessageEvent
    dispatched_to = {call.args[0].target_agent_name for call in call_args_list}
    
    assert "AgentA" in dispatched_to
    assert "AgentC" in dispatched_to
    assert "AgentB" not in dispatched_to # B is dependent on A, so not dispatched initially

    for call_arg in call_args_list:
        event = call_arg.args[0]
        assert isinstance(event, ProcessUserMessageEvent)
        assert isinstance(event.user_message, AgentInputUserMessage)
        assert event.user_message.metadata.get('source') == 'system_task_notifier'
        assert "Your task" in event.user_message.content
        assert "is now ready to start" in event.user_message.content

@pytest.mark.asyncio
async def test_notifies_when_dependency_completes_without_deliverables(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that a dependent task is notified after its dependency is completed, checking content."""
    notifier.start_monitoring()
    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)
    mock_team_manager.dispatch_user_message_to_agent.reset_mock() # Reset after initial dispatches

    task_a = next(t for t in single_dependency_plan.tasks if t.task_name == "task_a")

    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    
    assert isinstance(dispatched_event, ProcessUserMessageEvent)
    assert dispatched_event.target_agent_name == "AgentB"
    
    user_message = dispatched_event.user_message
    assert isinstance(user_message, AgentInputUserMessage)
    assert user_message.metadata.get('source') == 'system_task_notifier'
    assert "Your task 'task_b' is now ready to start." in user_message.content
    assert "Your task description:\nTask B." in user_message.content
    assert "deliverables" not in user_message.content  # Explicitly check that this is not present

@pytest.mark.asyncio
async def test_notifies_with_parent_deliverable_context(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that the notification includes context from a parent task's deliverables."""
    notifier.start_monitoring()
    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)
    mock_team_manager.dispatch_user_message_to_agent.reset_mock() # Reset after initial dispatches

    task_a = next(t for t in single_dependency_plan.tasks if t.task_name == "task_a")
    # Manually add a deliverable to the parent task before completing it
    deliverable = FileDeliverable(file_path="./output/a.txt", summary="Generated report A.", author_agent_name="AgentA")
    task_a.file_deliverables.append(deliverable)

    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    
    assert isinstance(dispatched_event, ProcessUserMessageEvent)
    assert dispatched_event.target_agent_name == "AgentB"
    
    user_message = dispatched_event.user_message
    assert isinstance(user_message, AgentInputUserMessage)
    assert user_message.metadata.get('source') == 'system_task_notifier'
    
    # Assert that all parts of the context-rich message are present
    assert "Your task is now unblocked." in user_message.content
    assert "context from the completed parent task(s):" in user_message.content
    assert "parent task 'task_a' produced the following deliverables:" in user_message.content
    assert "File: ./output/a.txt" in user_message.content
    assert "Summary: Generated report A." in user_message.content
    assert "Your task description:\nTask B." in user_message.content

@pytest.mark.asyncio
async def test_notifies_only_when_all_dependencies_are_complete(notifier, task_board, mock_team_manager, multi_dependency_plan):
    """Tests that a task with multiple dependencies is only notified after all are complete."""
    notifier.start_monitoring()
    task_board.load_task_plan(multi_dependency_plan)
    await asyncio.sleep(0.01) # No tasks without deps in this plan, so no initial dispatch
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()

    task_a = next(t for t in multi_dependency_plan.tasks if t.task_name == "task_a")
    task_b = next(t for t in multi_dependency_plan.tasks if t.task_name == "task_b")
    
    # Complete task_a, which is only one of the two dependencies for task_c
    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "AgentA")
    await asyncio.sleep(0.01)

    # Assert that task_c has NOT been notified yet
    mock_team_manager.dispatch_user_message_to_agent.assert_not_called()

    # Now complete task_b, the final dependency
    task_board.update_task_status(task_b.task_id, TaskStatus.COMPLETED, "AgentB")
    await asyncio.sleep(0.01)
    
    # Assert that task_c has NOW been notified
    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    
    assert isinstance(dispatched_event, ProcessUserMessageEvent)
    assert dispatched_event.target_agent_name == "AgentC"
    assert dispatched_event.user_message.metadata.get('source') == 'system_task_notifier'

@pytest.mark.asyncio
async def test_does_not_notify_twice(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that a task is not re-notified if it was already dispatched."""
    notifier.start_monitoring()
    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)
    
    # Task A and Task C were initially dispatched.
    assert mock_team_manager.dispatch_user_message_to_agent.call_count == 2
    mock_team_manager.dispatch_user_message_to_agent.reset_mock()

    task_c = next(t for t in single_dependency_plan.tasks if t.task_name == "task_c")
    # Change status of already dispatched task C (not relevant for unblocking others)
    task_board.update_task_status(task_c.task_id, TaskStatus.IN_PROGRESS, "AgentC")
    await asyncio.sleep(0.01)

    # No new dispatches are expected
    mock_team_manager.dispatch_user_message_to_agent.assert_not_called()

@pytest.mark.asyncio
async def test_resets_on_new_plan(notifier, task_board, mock_team_manager, single_dependency_plan):
    """Tests that dispatched state is cleared when a new plan is loaded."""
    notifier.start_monitoring()
    task_board.load_task_plan(single_dependency_plan)
    await asyncio.sleep(0.01)
    assert mock_team_manager.dispatch_user_message_to_agent.call_count == 2 # Initial dispatches for A and C

    mock_team_manager.dispatch_user_message_to_agent.reset_mock() # Reset to count dispatches for new plan
    
    new_plan = TaskPlan(overall_goal="New Goal", tasks=[Task(task_name="new_task", assignee_name="NewAgent", description="desc")])
    new_plan.hydrate_dependencies() # Ensure dependencies are hydrated for the new plan
    task_board.load_task_plan(new_plan)
    await asyncio.sleep(0.01)

    mock_team_manager.dispatch_user_message_to_agent.assert_called_once()
    dispatched_event = mock_team_manager.dispatch_user_message_to_agent.call_args.args[0]
    
    assert isinstance(dispatched_event, ProcessUserMessageEvent)
    assert dispatched_event.target_agent_name == "NewAgent"
    assert dispatched_event.user_message.metadata.get('source') == 'system_task_notifier'

