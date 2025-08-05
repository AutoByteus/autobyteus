# file: autobyteus/tests/unit_tests/agent_team/test_agent_team.py
import pytest
from unittest.mock import MagicMock, AsyncMock, create_autospec

from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent_team.runtime.agent_team_runtime import AgentTeamRuntime
from autobyteus.agent_team.events.agent_team_events import ProcessUserMessageEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

@pytest.fixture
def mock_runtime():
    mock_context = MagicMock()
    mock_context.config.coordinator_node.name = "Coordinator"
    mock_context.team_id = "mock-team-id"

    runtime = create_autospec(
        AgentTeamRuntime,
        instance=True,
        context=mock_context,
        is_running=False
    )

    runtime.start = MagicMock()
    runtime.submit_event = AsyncMock()

    return runtime

@pytest.fixture
def agent_team(mock_runtime):
    return AgentTeam(runtime=mock_runtime)

@pytest.mark.asyncio
async def test_post_message_starts_if_not_running(agent_team: AgentTeam, mock_runtime: MagicMock):
    """Tests that post_message calls start() if the runtime isn't running."""
    mock_runtime.is_running = False
    message = AgentInputUserMessage(content="test")
    
    await agent_team.post_message(message)
    
    mock_runtime.start.assert_called_once()
    mock_runtime.submit_event.assert_awaited_once()

@pytest.mark.asyncio
async def test_post_message_no_target_defaults_to_coordinator(agent_team: AgentTeam, mock_runtime: MagicMock):
    """Tests that post_message defaults to the coordinator if no target is specified."""
    mock_runtime.is_running = True
    message = AgentInputUserMessage(content="test")

    await agent_team.post_message(message, target_agent_name=None)

    mock_runtime.submit_event.assert_awaited_once()
    submitted_event = mock_runtime.submit_event.call_args.args[0]
    assert isinstance(submitted_event, ProcessUserMessageEvent)
    assert submitted_event.user_message is message
    assert submitted_event.target_agent_name == "Coordinator"

@pytest.mark.asyncio
async def test_post_message_with_target_uses_target(agent_team: AgentTeam, mock_runtime: MagicMock):
    """Tests that post_message uses the specified target agent name."""
    mock_runtime.is_running = True
    message = AgentInputUserMessage(content="test")
    target_name = "Specialist"

    await agent_team.post_message(message, target_agent_name=target_name)

    mock_runtime.submit_event.assert_awaited_once()
    submitted_event = mock_runtime.submit_event.call_args.args[0]
    assert isinstance(submitted_event, ProcessUserMessageEvent)
    assert submitted_event.target_agent_name == target_name
