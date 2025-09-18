# file: autobyteus/tests/unit_tests/task_management/converters/test_task_board_converter.py
import pytest
from autobyteus.task_management import (
    InMemoryTaskBoard,
    Task,
    TaskStatus,
    TaskBoardConverter,
    TaskStatusReportSchema
)
from autobyteus.task_management.deliverable import FileDeliverable

@pytest.fixture
def task_board_with_plan() -> InMemoryTaskBoard:
    """Provides a task board with a realistic plan loaded and statuses updated."""
    task_board = InMemoryTaskBoard(team_id="test_team_converter")
    
    tasks = [
        Task(task_name="task_one", assignee_name="Agent1", description="First task."),
        Task(task_name="task_two", assignee_name="Agent2", description="Second task.", dependencies=["task_one"]),
        Task(task_name="task_three", assignee_name="Agent1", description="Third task.", dependencies=["task_one"]),
    ]
    
    # Manually hydrate dependencies for the fixture
    name_to_id = {t.task_name: t.task_id for t in tasks}
    for task in tasks:
        task.dependencies = [name_to_id.get(dep_name, dep_name) for dep_name in task.dependencies]

    task_board.add_tasks(tasks)
    
    task_one = next(t for t in tasks if t.task_name == "task_one")
    task_three = next(t for t in tasks if t.task_name == "task_three")
    
    task_board.update_task_status(task_one.task_id, TaskStatus.COMPLETED, "Agent1")
    task_board.update_task_status(task_three.task_id, TaskStatus.IN_PROGRESS, "Agent1")
    
    # Add a deliverable to the completed task to test the converter
    task_one.file_deliverables.append(FileDeliverable(
        file_path="final_doc.md",
        summary="Completed the final documentation.",
        author_agent_name="Agent1"
    ))
    
    return task_board

def test_to_schema_with_loaded_plan(task_board_with_plan: InMemoryTaskBoard):
    """Tests that the converter correctly transforms a populated task board."""
    # Arrange
    overall_goal = "Test the converter."

    # Act
    report = TaskBoardConverter.to_schema(task_board_with_plan, overall_goal)
    
    # Assert
    assert isinstance(report, TaskStatusReportSchema)
    assert report.overall_goal == overall_goal
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

    # Check that deliverables are correctly converted
    assert len(task_one_report.file_deliverables) == 1
    assert task_three_report.file_deliverables == [] # Task three has no deliverables
    
    deliverable = task_one_report.file_deliverables[0]
    assert isinstance(deliverable, FileDeliverable)
    assert deliverable.file_path == "final_doc.md"
    assert deliverable.author_agent_name == "Agent1"
    assert not hasattr(deliverable, 'status')

def test_to_schema_with_empty_board():
    """Tests that the converter returns None for a board with no tasks."""
    # Arrange
    empty_board = InMemoryTaskBoard(team_id="empty_team")

    # Act
    report = TaskBoardConverter.to_schema(empty_board, "An empty goal.")

    # Assert
    assert report is None
