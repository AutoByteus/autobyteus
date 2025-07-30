# file: autobyteus/tests/unit_tests/workflow/streaming/test_agent_event_multiplexer.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.workflow.streaming.agent_event_multiplexer import AgentEventMultiplexer
from autobyteus.workflow.streaming.agent_event_bridge import AgentEventBridge

@pytest.fixture
def mock_notifier():
    return MagicMock()

@pytest.fixture
def multiplexer(mock_notifier, event_loop):
    # The `event_loop` fixture is provided by pytest-asyncio and ensures
    # a running event loop is available for the test. We must request it
    # to avoid the 'RuntimeError: no running event loop' when initializing
    # components that need access to the loop, like AgentEventMultiplexer.
    return AgentEventMultiplexer(workflow_id="wf-mux-test", notifier=mock_notifier, loop=event_loop)

@patch('autobyteus.workflow.streaming.agent_event_multiplexer.AgentEventBridge')
def test_start_bridging_creates_and_stores_bridge(MockAgentEventBridge, multiplexer: AgentEventMultiplexer):
    """
    Tests that start_bridging_agent_events correctly instantiates and stores an AgentEventBridge.
    """
    mock_agent = MagicMock()
    agent_name = "Agent1"

    multiplexer.start_bridging_agent_events(mock_agent, agent_name)

    # Verify AgentEventBridge was created with the correct parameters
    MockAgentEventBridge.assert_called_once_with(
        agent=mock_agent,
        agent_name=agent_name,
        notifier=multiplexer._notifier,
        loop=multiplexer._loop
    )

    # Verify the bridge was stored
    assert agent_name in multiplexer._bridges
    assert multiplexer._bridges[agent_name] is MockAgentEventBridge.return_value

@patch('autobyteus.workflow.streaming.agent_event_multiplexer.AgentEventBridge')
def test_start_bridging_is_idempotent(MockAgentEventBridge, multiplexer: AgentEventMultiplexer):
    """
    Tests that calling start_bridging_agent_events multiple times for the same agent does nothing after the first call.
    """
    mock_agent = MagicMock()
    agent_name = "Agent1"

    multiplexer.start_bridging_agent_events(mock_agent, agent_name)
    multiplexer.start_bridging_agent_events(mock_agent, agent_name)

    MockAgentEventBridge.assert_called_once()

@pytest.mark.asyncio
@patch('autobyteus.workflow.streaming.agent_event_multiplexer.AgentEventBridge')
async def test_shutdown_cancels_all_bridges(MockAgentEventBridge, multiplexer: AgentEventMultiplexer):
    """
    Tests that the shutdown method calls cancel() on all active bridges.
    """
    # Create mock bridge instances
    bridge1 = MockAgentEventBridge.return_value
    bridge1.cancel = AsyncMock()
    bridge2 = MagicMock(spec=AgentEventBridge)
    bridge2.cancel = AsyncMock()

    # Manually add them to the multiplexer's tracking dictionary
    multiplexer._bridges = {"Agent1": bridge1, "Agent2": bridge2}

    await multiplexer.shutdown()

    bridge1.cancel.assert_awaited_once()
    bridge2.cancel.assert_awaited_once()
    assert len(multiplexer._bridges) == 0 # Should be cleared after shutdown
