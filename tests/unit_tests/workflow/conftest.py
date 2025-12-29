# file: autobyteus/tests/unit_tests/workflow/conftest.py
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

from autobyteus.agent.context import AgentConfig
from autobyteus.workflow.context import (
    WorkflowConfig,
    WorkflowNodeConfig,
    WorkflowRuntimeState,
    WorkflowContext,
    TeamManager,
)
from autobyteus.workflow.status.workflow_status_manager import WorkflowStatusManager
from autobyteus.workflow.events.workflow_input_event_queue_manager import WorkflowInputEventQueueManager
from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier
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
def workflow_node_factory(agent_config_factory):
    """Provides a factory to create WorkflowNodeConfig objects."""
    def _factory(name: str) -> WorkflowNodeConfig:
        return WorkflowNodeConfig(node_definition=agent_config_factory(name))
    return _factory

@pytest.fixture
def sample_workflow_config(workflow_node_factory):
    """Provides a sample 2-node WorkflowConfig."""
    coordinator_node = workflow_node_factory("Coordinator")
    member_node = workflow_node_factory("Member")
    return WorkflowConfig(
        nodes=[coordinator_node, member_node],
        description="A test workflow",
        coordinator_node=coordinator_node
    )

@pytest.fixture
def workflow_runtime_state(sample_workflow_config):
    """Provides a default WorkflowRuntimeState."""
    return WorkflowRuntimeState(workflow_id=f"test_workflow_{uuid.uuid4().hex[:6]}")

@pytest.fixture
def mock_workflow_event_queue_manager():
    """Provides a mocked WorkflowInputEventQueueManager."""
    manager = MagicMock(spec=WorkflowInputEventQueueManager)
    manager.user_message_queue = AsyncMock(spec=asyncio.Queue)
    manager.internal_system_event_queue = AsyncMock(spec=asyncio.Queue)
    manager.enqueue_user_message = AsyncMock()
    manager.enqueue_internal_system_event = AsyncMock()
    return manager

@pytest.fixture
def mock_team_manager():
    """Provides a mocked TeamManager instance."""
    manager = MagicMock(spec=TeamManager)
    manager.set_agent_configs = MagicMock()
    manager.ensure_coordinator_is_ready = AsyncMock()
    manager.ensure_agent_is_ready = AsyncMock(return_value=None)
    return manager

@pytest.fixture
def mock_workflow_status_manager():
    """Provides a self-contained, mocked WorkflowStatusManager with async methods."""
    notifier_mock = AsyncMock(spec=WorkflowExternalEventNotifier)
    for attr_name in dir(WorkflowExternalEventNotifier):
        if attr_name.startswith("notify_"):
            setattr(notifier_mock, attr_name, MagicMock())

    manager = MagicMock(spec=WorkflowStatusManager)
    manager.notifier = notifier_mock
    for attr_name in dir(WorkflowStatusManager):
        if attr_name.startswith("notify_"):
            setattr(manager, attr_name, AsyncMock())
    return manager

@pytest.fixture
def workflow_context(sample_workflow_config, workflow_runtime_state, mock_workflow_event_queue_manager, mock_team_manager, mock_workflow_status_manager):
    """
    Provides a fully-composed and linked WorkflowContext ready for use in tests.
    Any test that requests this fixture will have a context with a status manager.
    """
    context = WorkflowContext(
        workflow_id=workflow_runtime_state.workflow_id,
        config=sample_workflow_config,
        state=workflow_runtime_state
    )
    # Simulate a post-bootstrap state:
    context.state.input_event_queues = mock_workflow_event_queue_manager
    context.state.team_manager = mock_team_manager
    # Link the mock status manager, ensuring context.status_manager is always available.
    context.state.status_manager_ref = mock_workflow_status_manager
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
