# file: autobyteus/tests/unit_tests/task_management/tools/test_update_task_status.py
import pytest
from unittest.mock import Mock, MagicMock

from autobyteus.task_management import InMemoryTaskBoard, TaskPlan, Task, TaskStatus
from autobyteus.task_management.tools import UpdateTaskStatus

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
async def test_execute_success(agent_context: Mock, task_board: InMemoryTaskBoard):
    """Tests successful execution of the UpdateTaskStatus tool."""
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
