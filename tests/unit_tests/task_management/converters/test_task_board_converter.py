# file: autobyteus/tests/unit_tests/task_management/converters/test_task_board_converter.py
import pytest
from autobyteus.task_management import (
    InMemoryTaskBoard,
    TaskPlan,
    Task,
    TaskStatus,
    TaskBoardConverter,
    TaskStatusReport
)

@pytest.fixture
def task_board_with_plan() -> InMemoryTaskBoard:
    """Provides a task board with a realistic plan loaded and statuses updated."""
    task_board = InMemoryTaskBoard(team_id="test_team_converter")
    
    plan = TaskPlan(
        overall_goal="Test the converter.",
        tasks=[
            Task(task_name="task_one", assignee_name="Agent1", description="First task."),
            Task(task_name="task_two", assignee_name="Agent2", description="Second task.", dependencies=["task_one"]),
            Task(task_name="task_three", assignee_name="Agent1", description="Third task.", dependencies=["task_one"]),
        ]
    )
    plan.hydrate_dependencies()
    task_board.load_task_plan(plan)
    
    task_one = next(t for t in plan.tasks if t.task_name == "task_one")
    task_three = next(t for t in plan.tasks if t.task_name == "task_three")
    
    task_board.update_task_status(task_one.task_id, TaskStatus.COMPLETED, "Agent1")
    task_board.update_task_status(task_three.task_id, TaskStatus.IN_PROGRESS, "Agent1")
    
    return task_board

def test_to_status_report_with_loaded_plan(task_board_with_plan: InMemoryTaskBoard):
    """Tests that the converter correctly transforms a populated task board."""
    # Act
    report = TaskBoardConverter.to_status_report(task_board_with_plan)
    
    # Assert
    assert isinstance(report, TaskStatusReport)
    assert report.overall_goal == "Test the converter."
    assert len(report.tasks) == 3
    
    # Find specific task reports
    task_one_report = next(t for t in report.tasks if t.task_name == "task_one")
    task_two_report = next(t for t in report.tasks if t.task_name == "task_two")
    task_three_report = next(t for t in report.tasks if t.task_name == "task_three")

    # Check statuses
    assert task_one_report.status == TaskStatus.COMPLETED
    assert task_two_report.status == TaskStatus.NOT_STARTED
    assert task_three_report.status == TaskStatus.IN_PROGRESS

    # Check dependencies are by name
    assert task_two_report.dependencies == ["task_one"]
    assert task_one_report.dependencies == []

def test_to_status_report_with_empty_board():
    """Tests that the converter returns None for a board with no plan."""
    # Arrange
    empty_board = InMemoryTaskBoard(team_id="empty_team")

    # Act
    report = TaskBoardConverter.to_status_report(empty_board)

    # Assert
    assert report is None
