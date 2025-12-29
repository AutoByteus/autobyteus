# file: autobyteus/tests/unit_tests/agent/status/test_discoverer.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.agent.status.discover import StatusTransitionDiscoverer
from autobyteus.agent.status.manager import AgentStatusManager
from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.status.transition_decorator import status_transition
from autobyteus.agent.status.transition_info import StatusTransitionInfo

class MockManager(AgentStatusManager):
    @status_transition(
        source_statuses=[AgentStatus.IDLE],
        target_status=AgentStatus.PROCESSING_USER_INPUT,
        description="Test transition"
    )
    def transition_method(self):
        pass

@pytest.fixture(autouse=True)
def mock_discoverer():
    """Fixture to automatically clear the discoverer's cache before and after each test."""
    StatusTransitionDiscoverer.clear_cache()
    yield
    StatusTransitionDiscoverer.clear_cache()

def test_discovery_returns_list_of_info_objects():
    """Tests that get_all_transitions() returns a non-empty list of StatusTransitionInfo objects."""
    # We use the real AgentStatusManager here, assuming it has at least one transition decorated.
    transitions = StatusTransitionDiscoverer.get_all_transitions()
    
    assert isinstance(transitions, list)
    assert len(transitions) > 0, "Should discover at least one transition from AgentStatusManager"
    
    for item in transitions:
        assert isinstance(item, StatusTransitionInfo)

def test_discover_basic():
    """Test normal discovery from a dedicated mock class."""
    transitions = StatusTransitionDiscoverer.get_all_transitions(MockManager)
    
    # We expect one transition from MockManager
    # Note: MockManager inherits from AgentStatusManager, so it might inherit transitions?
    # inspect.getmembers returns all members, including inherited ones.
    # So we should filter or check if our specific one is present.
    # But wait, our MockManager overrides nothing, just adds a method.
    
    found = False
    for info in transitions:
        if info.triggering_method == "transition_method":
            assert info.source_statuses == (AgentStatus.IDLE,)
            assert info.target_status == AgentStatus.PROCESSING_USER_INPUT
            assert info.description == "Test transition"
            found = True
            break
            
    assert found, "Did not find local transition_method in discovered transitions"

def test_discovery_caching():
    """Tests that discovery results are cached."""
    
    with patch('inspect.getmembers') as mock_getmembers:
        # Mock return value isn't strictly necessary if side_effect allows it, but let's just make it return empty to avoid errors
        mock_getmembers.return_value = []

        # First call should trigger inspect.getmembers
        StatusTransitionDiscoverer.get_all_transitions()
        mock_getmembers.assert_called_once()
        
        # Second call should use the cache and NOT trigger inspect.getmembers again
        StatusTransitionDiscoverer.get_all_transitions()
        mock_getmembers.assert_called_once() # Call count should still be 1

def test_clear_cache_works():
    """Tests that clear_cache forces re-discovery."""
    with patch('inspect.getmembers') as mock_getmembers:
        mock_getmembers.return_value = []

        # First call
        StatusTransitionDiscoverer.get_all_transitions()
        mock_getmembers.assert_called_once()
        
        # Clear cache
        StatusTransitionDiscoverer.clear_cache()
        
        # Second call should trigger discovery again
        StatusTransitionDiscoverer.get_all_transitions()
        assert mock_getmembers.call_count == 2
