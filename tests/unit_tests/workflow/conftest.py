# file: autobyteus/tests/unit_tests/workflow/conftest.py
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

from autobyteus.agent.context import AgentConfig
from autobyteus.agent.workflow.context import (
    WorkflowConfig,
    WorkflowNodeConfig,
    WorkflowRuntimeState,
    WorkflowContext,
)
from autobyteus.agent.workflow.phases.workflow_phase_manager import WorkflowPhaseManager
from autobyteus.agent.workflow.events.workflow_input_event_queue_manager import WorkflowInputEventQueueManager
from autobyteus.agent.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.agent.agent import Agent

# This conftest provides common, simplified fixtures for workflow-related unit tests.

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
            system_prompt=f"System prompt for {name}",
            tools=[] # Provide default empty list for tools to prevent TypeError
        )
    return _factory

@pytest.fixture
def workflow_node_factory(agent_config_factory):
    """Provides a factory to create WorkflowNodeConfig objects."""
    def _factory(name: str) -> WorkflowNodeConfig:
        return WorkflowNodeConfig(agent_config=agent_config_factory(name))
    return _factory

@pytest.fixture
def sample_workflow_config(workflow_node_factory):
    """Provides a sample 2-node WorkflowConfig."""
    coordinator_node = workflow_node_factory("Coordinator")
    # To test the coordinator prompt fix, we create its config without a system prompt
    coordinator_node.agent_config.system_prompt = None
    
    member_node = workflow_node_factory("Member")
    return WorkflowConfig(
        nodes=[coordinator_node, member_node],
        description="A test workflow",
        coordinator_node=coordinator_node
    )

@pytest.fixture
def workflow_runtime_state(sample_workflow_config):
    """Provides a default WorkflowRuntimeState."""
    workflow_id = f"test_workflow_{uuid.uuid4().hex[:6]}"
    return WorkflowRuntimeState(workflow_id=workflow_id)

@pytest.fixture
def mock_workflow_event_queue_manager():
    """Provides a mocked WorkflowInputEventQueueManager."""
    manager = MagicMock(spec=WorkflowInputEventQueueManager)
    manager.process_request_queue = AsyncMock(spec=asyncio.Queue)
    manager.internal_system_event_queue = AsyncMock(spec=asyncio.Queue)
    manager.enqueue_process_request = AsyncMock()
    manager.enqueue_internal_system_event = AsyncMock()
    return manager

@pytest.fixture
def mock_workflow_phase_manager():
    """Provides a mocked WorkflowPhaseManager with async methods."""
    # This fixture no longer depends on workflow_context, breaking the circular dependency.
    notifier_mock = AsyncMock(spec=WorkflowExternalEventNotifier)
    for attr_name in dir(WorkflowExternalEventNotifier):
        if attr_name.startswith("notify_"):
            setattr(notifier_mock, attr_name, MagicMock())

    manager = MagicMock(spec=WorkflowPhaseManager)
    manager.notifier = notifier_mock
    for attr_name in dir(WorkflowPhaseManager):
        if attr_name.startswith("notify_"):
            setattr(manager, attr_name, AsyncMock())
    return manager

@pytest.fixture
def workflow_context(sample_workflow_config, workflow_runtime_state, mock_workflow_event_queue_manager, mock_workflow_phase_manager):
    """
    Provides a fully-composed WorkflowContext ready for use in handler/step tests.
    """
    context = WorkflowContext(
        workflow_id=workflow_runtime_state.workflow_id,
        config=sample_workflow_config,
        state=workflow_runtime_state
    )
    # Simulate a post-bootstrap state for handlers/steps:
    context.state.input_event_queues = mock_workflow_event_queue_manager
    context.state.phase_manager_ref = mock_workflow_phase_manager
    return context

@pytest.fixture
def mock_agent():
    """Provides a mock Agent instance."""
    agent = MagicMock(spec=Agent)
    agent.agent_id = f"mock_agent_{uuid.uuid4().hex[:6]}"
    agent.is_running = False
    agent.start = MagicMock()
    agent.stop = AsyncMock()
    return agent
