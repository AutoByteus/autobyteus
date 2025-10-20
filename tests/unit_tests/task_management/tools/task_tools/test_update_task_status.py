# file: autobyteus/tests/unit_tests/task_management/tools/task_tools/test_update_task_status.py
import pytest
from unittest.mock import Mock, MagicMock

from autobyteus.task_management import InMemoryTaskPlan, Task, TaskStatus
from autobyteus.task_management.schemas import TaskDefinitionSchema
from autobyteus.task_management.tools import UpdateTaskStatus
from autobyteus.task_management.deliverable import FileDeliverable
from autobyteus.tools.usage.parsers import DefaultXmlToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def task_plan() -> InMemoryTaskPlan:
    """Provides a task plan with a simple plan loaded."""
    board = InMemoryTaskPlan(team_id="test_team_tool")
    # FIX: Use TaskDefinitionSchema to populate the plan
    task_defs = [
        TaskDefinitionSchema(task_name="task_a", assignee_name="Agent1", description="First task."),
        TaskDefinitionSchema(task_name="task_b", assignee_name="Agent2", description="Second task."),
    ]
    board.add_tasks(task_defs)
    return board

@pytest.fixture
def agent_context(task_plan: InMemoryTaskPlan) -> Mock:
    """Provides a mock agent context pointing to the task plan."""
    mock_context = Mock()
    mock_context.agent_id = "test_agent"
    mock_context.config.name = "TestAgent"
    
    mock_team_context = Mock()
    mock_team_context.state = MagicMock()
    mock_team_context.state.task_plan = task_plan
    
    mock_context.custom_data = {"team_context": mock_team_context}
    return mock_context

# --- Unit Tests (calling _execute directly) ---

@pytest.mark.asyncio
async def test_execute_status_only_success(agent_context: Mock, task_plan: InMemoryTaskPlan):
    """Tests successful execution of update_task_status with only a status update."""
    tool = UpdateTaskStatus()
    task_to_update = "task_a"
    new_status = "in_progress"
    
    task_id_to_check = next(t.task_id for t in task_plan.tasks if t.task_name == task_to_update)
    assert task_id_to_check == "task_0001" # Verify fixture correctness
    assert task_plan.task_statuses[task_id_to_check] == TaskStatus.NOT_STARTED

    result = await tool._execute(context=agent_context, task_name=task_to_update, status=new_status)

    assert result == f"Successfully updated status of task '{task_to_update}' to '{new_status}'."
    assert task_plan.task_statuses[task_id_to_check] == TaskStatus.IN_PROGRESS

@pytest.mark.asyncio
async def test_execute_with_deliverables_success(agent_context: Mock, task_plan: InMemoryTaskPlan):
    """Tests successful execution with both status update and deliverables."""
    tool = UpdateTaskStatus()
    task_to_update = "task_b"
    deliverables_payload = [
        {"file_path": "output/report.md", "summary": "Initial report draft."}
    ]

    result = await tool._execute(
        context=agent_context,
        task_name=task_to_update,
        status="completed",
        deliverables=deliverables_payload
    )

    assert "Successfully updated status of task 'task_b' to 'completed'" in result
    updated_task = next(t for t in task_plan.tasks if t.task_name == task_to_update)
    assert len(updated_task.file_deliverables) == 1
    assert updated_task.file_deliverables[0].file_path == "output/report.md"

@pytest.mark.asyncio
async def test_execute_with_invalid_deliverable_schema(agent_context: Mock, task_plan: InMemoryTaskPlan):
    """Tests that an invalid deliverable payload returns an error and does NOT update status."""
    tool = UpdateTaskStatus()
    task_to_update = "task_a"
    invalid_deliverables = [{"file_path": "output/bad.txt"}] # Missing 'summary'
    
    task_id_to_check = next(t.task_id for t in task_plan.tasks if t.task_name == task_to_update)
    assert task_plan.task_statuses[task_id_to_check] == TaskStatus.NOT_STARTED

    result = await tool._execute(
        context=agent_context,
        task_name=task_to_update,
        status="completed",
        deliverables=invalid_deliverables
    )
    
    assert "Error: Failed to process deliverables due to invalid data" in result
    assert task_plan.task_statuses[task_id_to_check] == TaskStatus.NOT_STARTED

# --- Integration Test (Full flow from XML) ---

@pytest.mark.asyncio
async def test_execute_with_input_from_xml_parser(agent_context: Mock, task_plan: InMemoryTaskPlan):
    """
    An integration test to verify the tool correctly processes input
    that has been parsed from a nested XML string for deliverables.
    """
    # Arrange
    tool = UpdateTaskStatus()
    task_to_update = "task_a"
    
    xml_tool_call = f"""
    <tool name="update_task_status">
        <arguments>
            <arg name="task_name">{task_to_update}</arg>
            <arg name="status">completed</arg>
            <arg name="deliverables">
                <item>
                    <arg name="file_path">src/main.py</arg>
                    <arg name="summary">Final version</arg>
                </item>
            </arg>
        </arguments>
    </tool>
    """
    
    # 1. Simulate the parser's output
    parser = DefaultXmlToolUsageParser()
    invocations = parser.parse(CompleteResponse(content=xml_tool_call))
    assert len(invocations) == 1
    parsed_arguments = invocations[0].arguments

    # 2. Act: Call the public execute method, which handles coercion
    result = await tool.execute(context=agent_context, **parsed_arguments)

    # 3. Assert
    assert "Successfully updated status" in result
    assert "and submitted 1 deliverable(s)" in result
    
    updated_task = next(t for t in task_plan.tasks if t.task_name == task_to_update)
    assert task_plan.task_statuses[updated_task.task_id] == TaskStatus.COMPLETED
    assert len(updated_task.file_deliverables) == 1
    
    deliverable = updated_task.file_deliverables[0]
    assert isinstance(deliverable, FileDeliverable)
    assert deliverable.file_path == "src/main.py"
    assert deliverable.author_agent_name == "TestAgent"
