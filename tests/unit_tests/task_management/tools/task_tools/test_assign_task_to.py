# file: autobyteus/tests/unit_tests/task_management/tools/task_tools/test_assign_task_to.py
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState, TeamManager
from autobyteus.task_management import InMemoryTaskPlan, Task
from autobyteus.task_management.schemas import TaskDefinitionSchema
from autobyteus.task_management.tools import AssignTaskTo
from autobyteus.agent_team.events import InterAgentMessageRequestEvent

@pytest.fixture
def tool() -> AssignTaskTo:
    """Provides a fresh instance of the AssignTaskTo tool."""
    return AssignTaskTo()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    """Provides a mock AgentContext."""
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "sender_agent_id"
    mock_context.config = Mock()
    mock_context.config.name = "SenderAgent"
    mock_context.custom_data = {}
    return mock_context

@pytest.fixture
def mock_team_context() -> AgentTeamContext:
    """Provides a mock AgentTeamContext with mocks for task plan and team manager."""
    mock_context = Mock(spec=AgentTeamContext)
    mock_state = Mock(spec=AgentTeamRuntimeState)
    
    # Use a real InMemoryTaskPlan to test dependency name resolution in the notification message
    mock_state.task_plan = InMemoryTaskPlan(team_id="test_team")
    mock_state.task_plan.add_task(Task(task_name="setup", assignee_name="a", description="d"))
    
    mock_team_manager = Mock(spec=TeamManager)
    mock_team_manager.dispatch_inter_agent_message_request = AsyncMock()
    
    mock_context.state = mock_state
    mock_context.team_manager = mock_team_manager
    return mock_context


def test_get_name(tool: AssignTaskTo):
    assert tool.get_name() == "AssignTaskTo"

def test_get_description(tool: AssignTaskTo):
    assert "assigns a single new task to a specific team member" in tool.get_description()

@pytest.mark.asyncio
async def test_execute_success(tool: AssignTaskTo, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests the happy path: task is published and notification is sent."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    task_plan = mock_team_context.state.task_plan
    team_manager = mock_team_context.team_manager
    
    task_def = TaskDefinitionSchema(
        task_name="new_delegated_task",
        assignee_name="RecipientAgent",
        description="Please do this work.",
        dependencies=["setup"]
    )
    
    # Act
    result = await tool._execute(mock_agent_context, **task_def.model_dump())

    # Assert
    assert result == "Successfully assigned task 'new_delegated_task' to agent 'RecipientAgent' and sent a notification."
    
    # Assert Action 1: Task was added to the board
    assert len(task_plan.tasks) == 2
    newly_added_task = next((t for t in task_plan.tasks if t.task_name == "new_delegated_task"), None)
    assert newly_added_task is not None
    assert newly_added_task.assignee_name == "RecipientAgent"

    # Assert Action 2: Notification was sent via TeamManager
    team_manager.dispatch_inter_agent_message_request.assert_awaited_once()
    call_args, _ = team_manager.dispatch_inter_agent_message_request.call_args
    sent_event: InterAgentMessageRequestEvent = call_args[0]
    
    assert isinstance(sent_event, InterAgentMessageRequestEvent)
    assert sent_event.sender_agent_id == "sender_agent_id"
    assert sent_event.recipient_name == "RecipientAgent"
    assert sent_event.message_type == "task_assignment"
    assert "**Task Name**: 'new_delegated_task'" in sent_event.content
    assert "**Description**: Please do this work." in sent_event.content
    assert "**Dependencies**: setup" in sent_event.content # Check dependency name resolution

@pytest.mark.asyncio
async def test_execute_no_team_context(tool: AssignTaskTo, mock_agent_context: AgentContext):
    """Tests failure when team context is missing."""
    result = await tool._execute(mock_agent_context, task_name="t", assignee_name="a", description="d")
    assert "Error: Team context is not available." in result

@pytest.mark.asyncio
async def test_execute_no_task_plan(tool: AssignTaskTo, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests failure when the task plan is not initialized."""
    mock_team_context.state.task_plan = None
    mock_agent_context.custom_data["team_context"] = mock_team_context
    result = await tool._execute(mock_agent_context, task_name="t", assignee_name="a", description="d")
    assert "Error: Task plan has not been initialized" in result

@pytest.mark.asyncio
async def test_execute_degraded_success_no_team_manager(tool: AssignTaskTo, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests that the task is added even if the team manager is missing for notification."""
    # Arrange
    mock_team_context.team_manager = None # Remove the team manager
    mock_agent_context.custom_data["team_context"] = mock_team_context
    task_plan = mock_team_context.state.task_plan

    task_def = TaskDefinitionSchema(
        task_name="delegated_task_no_notify",
        assignee_name="RecipientAgent",
        description="Work to be done.",
    )

    # Act
    result = await tool._execute(mock_agent_context, **task_def.model_dump())

    # Assert
    assert "Successfully published task 'delegated_task_no_notify', but could not send a direct notification" in result
    
    # Assert that the task was still added to the board
    assert len(task_plan.tasks) == 2
    newly_added_task = next((t for t in task_plan.tasks if t.task_name == "delegated_task_no_notify"), None)
    assert newly_added_task is not None

@pytest.mark.asyncio
async def test_execute_invalid_task_definition(tool: AssignTaskTo, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests failure when provided arguments don't match the schema."""
    mock_agent_context.custom_data["team_context"] = mock_team_context
    task_plan = mock_team_context.state.task_plan
    
    invalid_kwargs = {
        "task_name": "invalid_task"
        # Missing assignee_name and description
    }
    
    result = await tool._execute(mock_agent_context, **invalid_kwargs)

    assert "Error: Invalid task definition provided" in result
    # Assert that no new task was added
    assert len(task_plan.tasks) == 1
