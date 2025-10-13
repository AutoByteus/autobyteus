# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_task_notifier_initialization_step.py
import pytest
from unittest.mock import MagicMock, patch

from autobyteus.agent_team.bootstrap_steps import TaskNotifierInitializationStep
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamConfig, TeamNodeConfig, AgentTeamRuntimeState
from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode
from autobyteus.task_management import InMemoryTaskPlan

@pytest.fixture
def step_instance() -> TaskNotifierInitializationStep:
    """Provides a clean instance of the step."""
    return TaskNotifierInitializationStep()

@pytest.mark.asyncio
async def test_execute_skips_in_manual_mode(step_instance: TaskNotifierInitializationStep, agent_team_context: AgentTeamContext):
    """
    Tests that the step does nothing and succeeds when the team is in AGENT_MANUAL_NOTIFICATION mode.
    """
    # Arrange - Create a new config with the desired mode
    manual_config = AgentTeamConfig(
        name=agent_team_context.config.name,
        description=agent_team_context.config.description,
        nodes=agent_team_context.config.nodes,
        coordinator_node=agent_team_context.config.coordinator_node,
        task_notification_mode=TaskNotificationMode.AGENT_MANUAL_NOTIFICATION
    )
    agent_team_context.config = manual_config
    
    # Act
    with patch("autobyteus.agent_team.bootstrap_steps.task_notifier_initialization_step.SystemEventDrivenAgentTaskNotifier") as MockNotifier:
        success = await step_instance.execute(agent_team_context, agent_team_context.phase_manager)

    # Assert
    assert success is True
    MockNotifier.assert_not_called()
    assert agent_team_context.state.task_notifier is None

@pytest.mark.asyncio
async def test_execute_initializes_in_event_driven_mode(step_instance: TaskNotifierInitializationStep, agent_team_context: AgentTeamContext):
    """
    Tests that the step correctly initializes the notifier in SYSTEM_EVENT_DRIVEN mode.
    """
    # Arrange - Create a new config with the desired mode
    event_driven_config = AgentTeamConfig(
        name=agent_team_context.config.name,
        description=agent_team_context.config.description,
        nodes=agent_team_context.config.nodes,
        coordinator_node=agent_team_context.config.coordinator_node,
        task_notification_mode=TaskNotificationMode.SYSTEM_EVENT_DRIVEN
    )
    agent_team_context.config = event_driven_config
    agent_team_context.state.task_plan = MagicMock(spec=InMemoryTaskPlan) # Ensure task plan exists

    # Act
    with patch("autobyteus.agent_team.bootstrap_steps.task_notifier_initialization_step.SystemEventDrivenAgentTaskNotifier") as MockNotifierClass:
        mock_notifier_instance = MockNotifierClass.return_value
        success = await step_instance.execute(agent_team_context, agent_team_context.phase_manager)

    # Assert
    assert success is True
    MockNotifierClass.assert_called_once_with(
        task_plan=agent_team_context.state.task_plan,
        team_manager=agent_team_context.team_manager
    )
    mock_notifier_instance.start_monitoring.assert_called_once()
    assert agent_team_context.state.task_notifier is mock_notifier_instance

@pytest.mark.asyncio
async def test_execute_fails_if_task_plan_missing(step_instance: TaskNotifierInitializationStep, agent_team_context: AgentTeamContext):
    """
    Tests that the step fails in event-driven mode if the task plan isn't initialized.
    """
    # Arrange - Create a new config with the desired mode
    event_driven_config = AgentTeamConfig(
        name=agent_team_context.config.name,
        description=agent_team_context.config.description,
        nodes=agent_team_context.config.nodes,
        coordinator_node=agent_team_context.config.coordinator_node,
        task_notification_mode=TaskNotificationMode.SYSTEM_EVENT_DRIVEN
    )
    agent_team_context.config = event_driven_config
    agent_team_context.state.task_plan = None

    # Act
    success = await step_instance.execute(agent_team_context, agent_team_context.phase_manager)

    # Assert
    assert success is False

@pytest.mark.asyncio
async def test_execute_fails_if_team_manager_missing(step_instance: TaskNotifierInitializationStep, agent_team_context: AgentTeamContext):
    """
    Tests that the step fails in event-driven mode if the team manager isn't available.
    """
    # Arrange - Create a new config with the desired mode
    event_driven_config = AgentTeamConfig(
        name=agent_team_context.config.name,
        description=agent_team_context.config.description,
        nodes=agent_team_context.config.nodes,
        coordinator_node=agent_team_context.config.coordinator_node,
        task_notification_mode=TaskNotificationMode.SYSTEM_EVENT_DRIVEN
    )
    agent_team_context.config = event_driven_config
    agent_team_context.state.task_plan = MagicMock(spec=InMemoryTaskPlan)
    agent_team_context.state.team_manager = None

    # Act
    success = await step_instance.execute(agent_team_context, agent_team_context.phase_manager)

    # Assert
    assert success is False
