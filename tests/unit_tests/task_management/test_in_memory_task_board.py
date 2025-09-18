# file: autobyteus/tests/unit_tests/task_management/test_in_memory_task_board.py
import pytest
from unittest.mock import patch, ANY

from autobyteus.events.event_types import EventType
from autobyteus.task_management import (
    InMemoryTaskBoard,
    Task,
    TaskStatus,
)
from autobyteus.task_management.events import TasksAddedEvent, TaskStatusUpdatedEvent

@pytest.fixture
def basic_plan_tasks() -> list[Task]:
    """Provides a list of two independent tasks."""
    tasks = [
        Task(task_name="task_one", assignee_name="Agent1", description="First task."),
        Task(task_name="task_two", assignee_name="Agent2", description="Second task."),
    ]
    # No dependencies to hydrate
    return tasks

@pytest.fixture
def dependent_plan_tasks() -> list[Task]:
    """
    Provides a list of tasks with dependencies:
    A -> (B, C)
    B -> D
    """
    tasks = [
        Task(task_name="A", assignee_name="Agent1", description="Task A, no dependencies."),
        Task(task_name="B", assignee_name="Agent2", description="Task B, depends on A.", dependencies=["A"]),
        Task(task_name="C", assignee_name="Agent1", description="Task C, depends on A.", dependencies=["A"]),
        Task(task_name="D", assignee_name="Agent2", description="Task D, depends on B.", dependencies=["B"]),
    ]
    
    # Manually hydrate dependencies for the fixture
    name_to_id = {t.task_name: t.task_id for t in tasks}
    for task in tasks:
        task.dependencies = [name_to_id.get(dep_name, dep_name) for dep_name in task.dependencies]

    return tasks

@pytest.fixture
def task_board() -> InMemoryTaskBoard:
    """Provides a clean instance of the task board for each test."""
    return InMemoryTaskBoard(team_id="test_team")

# --- Test Initialization and Adding Tasks ---

def test_initialization(task_board: InMemoryTaskBoard):
    """Tests that the task board is initialized in a clean state."""
    assert task_board.team_id == "test_team"
    assert not task_board.tasks
    assert not task_board.task_statuses
    assert not task_board._task_map

def test_add_tasks_success(task_board: InMemoryTaskBoard, basic_plan_tasks: list[Task]):
    """Tests that adding tasks correctly sets up the board and emits an event."""
    with patch.object(task_board, 'emit') as mock_emit:
        result = task_board.add_tasks(basic_plan_tasks)
        
        assert result is True
        assert len(task_board.tasks) == 2
        assert len(task_board.task_statuses) == 2
        
        task_one_id = next(t.task_id for t in basic_plan_tasks if t.task_name == "task_one")
        assert task_board.task_statuses[task_one_id] == TaskStatus.NOT_STARTED

        # Check that the correct event was emitted
        mock_emit.assert_called_once()
        event_name, kwargs = mock_emit.call_args
        assert event_name[0] == EventType.TASK_BOARD_TASKS_ADDED
        payload = kwargs['payload']
        assert isinstance(payload, TasksAddedEvent)
        assert payload.tasks == basic_plan_tasks

def test_add_task_success(task_board: InMemoryTaskBoard):
    """Tests that the convenience method for adding a single task works."""
    new_task = Task(task_name="single_task", assignee_name="SoloAgent", description="A single task.")
    with patch.object(task_board, 'add_tasks', return_value=True) as mock_add_tasks:
        result = task_board.add_task(new_task)
        assert result is True
        mock_add_tasks.assert_called_once_with([new_task])

# --- Test Status Updates ---

def test_update_task_status_success(task_board: InMemoryTaskBoard, basic_plan_tasks: list[Task]):
    """Tests that updating a status works correctly and emits an event."""
    task_board.add_tasks(basic_plan_tasks)
    task_one_id = next(t.task_id for t in basic_plan_tasks if t.task_name == "task_one")
    
    with patch.object(task_board, 'emit') as mock_emit:
        result = task_board.update_task_status(task_one_id, TaskStatus.IN_PROGRESS, "Agent1")

        assert result is True
        assert task_board.task_statuses[task_one_id] == TaskStatus.IN_PROGRESS

        # Check that the correct event was emitted
        # The add_tasks call is outside the patch context, so we expect only one call here.
        mock_emit.assert_called_once_with(EventType.TASK_BOARD_STATUS_UPDATED, payload=ANY)
        
        # We can still inspect the call's payload for more detailed assertions
        last_call_args, last_call_kwargs = mock_emit.call_args
        payload = last_call_kwargs['payload']
        assert isinstance(payload, TaskStatusUpdatedEvent)
        assert payload.task_id == task_one_id
        assert payload.new_status == TaskStatus.IN_PROGRESS
        assert payload.agent_name == "Agent1"

def test_update_task_status_non_existent_task(task_board: InMemoryTaskBoard):
    """Tests that updating a non-existent task fails gracefully."""
    result = task_board.update_task_status("fake_id", TaskStatus.COMPLETED, "AgentX")
    assert result is False

# --- Tests for get_next_runnable_tasks ---

def test_get_runnable_no_tasks_added(task_board: InMemoryTaskBoard):
    """Tests that no tasks are runnable if no tasks have been added."""
    assert task_board.get_next_runnable_tasks() == []

def test_get_runnable_no_dependencies(task_board: InMemoryTaskBoard, basic_plan_tasks: list[Task]):
    """Tests that all tasks are runnable if there are no dependencies."""
    task_board.add_tasks(basic_plan_tasks)
    runnable = task_board.get_next_runnable_tasks()
    
    assert len(runnable) == 2
    runnable_names = {t.task_name for t in runnable}
    assert runnable_names == {"task_one", "task_two"}

def test_get_runnable_with_dependencies_initial_state(task_board: InMemoryTaskBoard, dependent_plan_tasks: list[Task]):
    """Tests that only tasks with no dependencies are initially runnable."""
    task_board.add_tasks(dependent_plan_tasks)
    runnable = task_board.get_next_runnable_tasks()

    assert len(runnable) == 1
    assert runnable[0].task_name == "A"

def test_get_runnable_dependency_completed(task_board: InMemoryTaskBoard, dependent_plan_tasks: list[Task]):
    """Tests that tasks become runnable once their dependencies are met."""
    task_board.add_tasks(dependent_plan_tasks)
    task_a = next(t for t in dependent_plan_tasks if t.task_name == "A")
    
    # Complete task A
    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "Agent1")
    runnable = task_board.get_next_runnable_tasks()
    
    # Now that A is complete, B and C should be runnable
    assert len(runnable) == 2
    runnable_names = {t.task_name for t in runnable}
    assert runnable_names == {"B", "C"}

def test_get_runnable_multi_level_dependency_flow(task_board: InMemoryTaskBoard, dependent_plan_tasks: list[Task]):
    """Tests the flow of runnable tasks through a multi-level dependency chain."""
    task_board.add_tasks(dependent_plan_tasks)
    task_a = next(t for t in dependent_plan_tasks if t.task_name == "A")
    task_b = next(t for t in dependent_plan_tasks if t.task_name == "B")
    
    # 1. Initial state: Only A is runnable
    assert {t.task_name for t in task_board.get_next_runnable_tasks()} == {"A"}

    # 2. Complete A: B and C become runnable
    task_board.update_task_status(task_a.task_id, TaskStatus.COMPLETED, "Agent1")
    assert {t.task_name for t in task_board.get_next_runnable_tasks()} == {"B", "C"}
    
    # 3. Complete B: D becomes runnable, and C is still runnable
    task_board.update_task_status(task_b.task_id, TaskStatus.COMPLETED, "Agent2")
    assert {t.task_name for t in task_board.get_next_runnable_tasks()} == {"C", "D"}

def test_get_runnable_with_failed_dependency(task_board: InMemoryTaskBoard, dependent_plan_tasks: list[Task]):
    """Tests that tasks are not runnable if their dependencies have failed."""
    task_board.add_tasks(dependent_plan_tasks)
    task_a = next(t for t in dependent_plan_tasks if t.task_name == "A")

    # Mark dependency A as FAILED
    task_board.update_task_status(task_a.task_id, TaskStatus.FAILED, "Agent1")
    runnable = task_board.get_next_runnable_tasks()
    
    # B and C depend on A, so they should not become runnable.
    assert len(runnable) == 0

def test_get_runnable_when_task_in_progress(task_board: InMemoryTaskBoard, dependent_plan_tasks: list[Task]):
    """Tests that a task in progress is not returned as runnable."""
    task_board.add_tasks(dependent_plan_tasks)
    task_a = next(t for t in dependent_plan_tasks if t.task_name == "A")
    
    # Initially, A is runnable
    assert {t.task_name for t in task_board.get_next_runnable_tasks()} == {"A"}
    
    # Start task A
    task_board.update_task_status(task_a.task_id, TaskStatus.IN_PROGRESS, "Agent1")
    
    # Now, no tasks should be runnable (A is no longer NOT_STARTED, and B/C are blocked)
    assert task_board.get_next_runnable_tasks() == []

# --- Test get_status_overview ---

def test_get_status_overview(task_board: InMemoryTaskBoard, basic_plan_tasks: list[Task]):
    """Tests that the status overview is correct for both empty and loaded boards."""
    # Test on empty board
    overview_empty = task_board.get_status_overview()
    assert overview_empty["task_statuses"] == {}
    assert overview_empty["tasks"] == []

    # Test on loaded board
    task_board.add_tasks(basic_plan_tasks)
    task_one_id = next(t.task_id for t in basic_plan_tasks if t.task_name == "task_one")
    task_board.update_task_status(task_one_id, TaskStatus.COMPLETED, "Agent1")

    overview_loaded = task_board.get_status_overview()
    assert len(overview_loaded["tasks"]) == 2
    assert overview_loaded["task_statuses"][task_one_id] == "completed"
