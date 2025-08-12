# file: autobyteus/tests/unit_tests/task_management/tools/test_update_task_status.py
import pytest
from unittest.mock import Mock, MagicMock

from autobyteus.task_management import InMemoryTaskBoard, TaskPlan, Task, TaskStatus
from autobyteus.task_management.tools import UpdateTaskStatus
from autobyteus.task_management.deliverable import FileDeliverable

@pytest.fixture
def task_board() -> InMemoryTaskBoard:
    """Provides a task board with a simple plan loaded."""
    board = InMemoryTaskBoard(team_id="test_team_tool")
    plan = TaskPlan(
        overall_goal="Test the UpdateTaskStatus tool.",
        tasks=[
            Task(task_name="task_a", assignee_name="Agent1", description="First task."),
            Task(task_name="task_b", assignee_name="Agent2", description="Second task."),
        ]
    )
    plan.hydrate_dependencies()
    board.load_task_plan(plan)
    return board

@pytest.fixture
def agent_context(task_board: InMemoryTaskBoard) -> Mock:
    """Provides a mock agent context pointing to the task board."""
    mock_context = Mock()
    mock_context.agent_id = "test_agent"
    mock_context.config.name = "TestAgent"
    
    mock_team_context = Mock()
    mock_team_context.state = MagicMock()
    mock_team_context.state.task_board = task_board
    
    mock_context.custom_data = {"team_context": mock_team_context}
    return mock_context

@pytest.mark.asyncio
async def test_execute_status_only_success(agent_context: Mock, task_board: InMemoryTaskBoard):
    """Tests successful execution of UpdateTaskStatus with only a status update."""
    # Arrange
    tool = UpdateTaskStatus()
    task_to_update = "task_a"
    new_status = "in_progress"
    
    task_id_to_check = next(t.task_id for t in task_board.current_plan.tasks if t.task_name == task_to_update)
    assert task_board.task_statuses[task_id_to_check] == TaskStatus.NOT_STARTED

    # Act
    result = await tool._execute(context=agent_context, task_name=task_to_update, status=new_status)

    # Assert
    assert result == f"Successfully updated status of task '{task_to_update}' to '{new_status}'."
    assert task_board.task_statuses[task_id_to_check] == TaskStatus.IN_PROGRESS

@pytest.mark.asyncio
async def test_execute_with_deliverables_success(agent_context: Mock, task_board: InMemoryTaskBoard):
    """Tests successful execution with both status update and deliverables."""
    # Arrange
    tool = UpdateTaskStatus()
    task_to_update = "task_b"
    
    deliverables_payload = [
        {"file_path": "output/report.md", "summary": "Initial report draft."},
        {"file_path": "output/data.csv", "summary": "Cleaned the raw data."}
    ]

    # Act
    result = await tool._execute(
        context=agent_context,
        task_name=task_to_update,
        status="completed",
        deliverables=deliverables_payload
    )

    # Assert
    assert "Successfully updated status of task 'task_b' to 'completed'" in result
    assert "and submitted 2 deliverable(s)" in result
    
    # Check the task board state directly
    updated_task = next(t for t in task_board.current_plan.tasks if t.task_name == task_to_update)
    assert task_board.task_statuses[updated_task.task_id] == TaskStatus.COMPLETED
    assert len(updated_task.file_deliverables) == 2
    
    first_deliverable = updated_task.file_deliverables[0]
    assert isinstance(first_deliverable, FileDeliverable)
    assert first_deliverable.file_path == "output/report.md"
    assert first_deliverable.summary == "Initial report draft."
    assert first_deliverable.author_agent_name == "TestAgent"

@pytest.mark.asyncio
async def test_execute_with_invalid_deliverable_schema(agent_context: Mock, task_board: InMemoryTaskBoard):
    """Tests that an invalid deliverable payload returns an error and does NOT update status."""
    # Arrange
    tool = UpdateTaskStatus()
    task_to_update = "task_a"
    
    # Payload is missing the required 'summary' field
    invalid_deliverables = [{"file_path": "output/bad.txt"}]
    
    task_id_to_check = next(t.task_id for t in task_board.current_plan.tasks if t.task_name == task_to_update)
    assert task_board.task_statuses[task_id_to_check] == TaskStatus.NOT_STARTED

    # Act
    result = await tool._execute(
        context=agent_context,
        task_name=task_to_update,
        status="completed",
        deliverables=invalid_deliverables
    )
    
    # Assert
    # CORRECTED: Check for the new, more accurate error message.
    assert "Error: Failed to process deliverables due to invalid data" in result
    assert "Task status was NOT updated" in result
    
    # CORRECTED: Check that the status was NOT updated because the operation failed early.
    updated_task = next(t for t in task_board.current_plan.tasks if t.task_name == task_to_update)
    assert task_board.task_statuses[updated_task.task_id] == TaskStatus.NOT_STARTED
    # And that no deliverables were added
    assert len(updated_task.file_deliverables) == 0

@pytest.mark.asyncio
async def test_execute_task_not_found(agent_context: Mock):
    """Tests execution when the task_name does not exist on the plan."""
    # Arrange
    tool = UpdateTaskStatus()
    task_to_update = "non_existent_task"
    new_status = "completed"

    # Act
    result = await tool._execute(context=agent_context, task_name=task_to_update, status=new_status)

    # Assert
    assert "Error: Failed to update status" in result
    assert "task name does not exist" in result

@pytest.mark.asyncio
async def test_execute_invalid_status(agent_context: Mock):
    """Tests execution with an invalid status string."""
    # Arrange
    tool = UpdateTaskStatus()
    task_to_update = "task_b"
    new_status = "done" # Invalid status

    # Act
    result = await tool._execute(context=agent_context, task_name=task_to_update, status=new_status)

    # Assert
    assert "Error: Invalid status 'done'" in result

@pytest.mark.asyncio
async def test_execute_no_plan_loaded(agent_context: Mock, task_board: InMemoryTaskBoard):
    """Tests execution when no plan is on the board."""
    # Arrange
    task_board.current_plan = None # Simulate no plan
    tool = UpdateTaskStatus()

    # Act
    result = await tool._execute(context=agent_context, task_name="task_a", status="in_progress")

    # Assert
    assert "Error: No task plan is currently loaded" in result

@pytest.mark.asyncio
async def test_execute_no_team_context():
    """Tests execution when team context is missing."""
    # Arrange
    tool = UpdateTaskStatus()
    mock_context = Mock()
    mock_context.agent_id = "lonely_agent"
    mock_context.config.name = "LonelyAgent"
    mock_context.custom_data = {} # No team context

    # Act
    result = await tool._execute(context=mock_context, task_name="task_a", status="in_progress")
    
    # Assert
    assert "Error: Team context is not available" in result
