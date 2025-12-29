# file: autobyteus/tests/unit_tests/agent_team/conftest.py
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.context import (
    AgentTeamConfig,
    TeamNodeConfig,
    AgentTeamRuntimeState,
    AgentTeamContext,
    TeamManager,
)
from autobyteus.agent_team.status.agent_team_status_manager import AgentTeamStatusManager
from autobyteus.agent_team.events.agent_team_input_event_queue_manager import AgentTeamInputEventQueueManager
from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.agent.agent import Agent

@pytest.fixture
def mock_llm_instance():
    """Provides a mocked BaseLLM instance."""
    llm = MagicMock(spec=BaseLLM)
    llm.config = LLMConfig(system_message="Initial system message.")
    return llm

@pytest.fixture
def agent_config_factory(mock_llm_instance):
    """Provides a factory to create mock AgentConfig objects."""
    def _factory(name: str) -> AgentConfig:
        return AgentConfig(
            name=name,
            role=f"{name}_role",
            description=f"Description for {name}",
            llm_instance=mock_llm_instance,
            tools=[]
        )
    return _factory

@pytest.fixture
def mock_agent_config():
    """Provides a mocked AgentConfig with necessary attributes."""
    mock_config = MagicMock(spec=AgentConfig)
    mock_config.name = "MockAgent"
    mock_config.role = "MockRole"
    return mock_config

@pytest.fixture
def team_node_factory(agent_config_factory):
    """Provides a factory to create TeamNodeConfig objects."""
    def _factory(name: str) -> TeamNodeConfig:
        return TeamNodeConfig(node_definition=agent_config_factory(name))
    return _factory

@pytest.fixture
def sample_agent_team_config(team_node_factory):
    """Provides a sample 2-node AgentTeamConfig."""
    coordinator_node = team_node_factory("Coordinator")
    member_node = team_node_factory("Member")
    return AgentTeamConfig(
        name="Test Team",
        nodes=(coordinator_node, member_node),
        description="A test agent team",
        coordinator_node=coordinator_node
    )

@pytest.fixture
def agent_team_runtime_state(sample_agent_team_config):
    """Provides a default AgentTeamRuntimeState."""
    return AgentTeamRuntimeState(team_id=f"test_team_{uuid.uuid4().hex[:6]}")

@pytest.fixture
def mock_agent_team_event_queue_manager():
    """Provides a mocked AgentTeamInputEventQueueManager."""
    manager = MagicMock(spec=AgentTeamInputEventQueueManager)
    manager.user_message_queue = AsyncMock(spec=asyncio.Queue)
    manager.internal_system_event_queue = AsyncMock(spec=asyncio.Queue)
    manager.enqueue_user_message = AsyncMock()
    manager.enqueue_internal_system_event = AsyncMock()
    return manager

@pytest.fixture
def mock_team_manager():
    """Provides a mocked TeamManager instance."""
    manager = MagicMock(spec=TeamManager)
    manager.ensure_coordinator_is_ready = AsyncMock()
    manager.ensure_node_is_ready = AsyncMock(return_value=None)
    return manager

@pytest.fixture
def mock_agent_team_status_manager():
    """Provides a self-contained, mocked AgentTeamStatusManager with async methods."""
    notifier_mock = AsyncMock(spec=AgentTeamExternalEventNotifier)
    for attr_name in dir(AgentTeamExternalEventNotifier):
        if attr_name.startswith("notify_"):
            setattr(notifier_mock, attr_name, MagicMock())

    manager = MagicMock(spec=AgentTeamStatusManager)
    manager.notifier = notifier_mock
    manager.emit_status_update = AsyncMock()
    return manager

@pytest.fixture
def agent_team_context(sample_agent_team_config, agent_team_runtime_state, mock_agent_team_event_queue_manager, mock_team_manager, mock_agent_team_status_manager):
    """
    Provides a fully-composed and linked AgentTeamContext ready for use in tests.
    Any test that requests this fixture will have a context with a status manager.
    """
    context = AgentTeamContext(
        team_id=agent_team_runtime_state.team_id,
        config=sample_agent_team_config,
        state=agent_team_runtime_state
    )
    # Simulate a post-bootstrap state:
    context.state.input_event_queues = mock_agent_team_event_queue_manager
    context.state.team_manager = mock_team_manager
    # Link the mock status manager, ensuring context.status_manager is always available.
    context.state.status_manager_ref = mock_agent_team_status_manager
    return context

@pytest.fixture
def mock_agent():
    """Provides a mock Agent instance."""
    agent = MagicMock(spec=Agent)
    agent.agent_id = f"mock_agent_{uuid.uuid4().hex[:6]}"
    agent.is_running = False
    agent.start = MagicMock()
    agent.stop = AsyncMock()
    agent.post_user_message = AsyncMock()
    agent.post_inter_agent_message = AsyncMock()
    agent.context = MagicMock()
    return agent
