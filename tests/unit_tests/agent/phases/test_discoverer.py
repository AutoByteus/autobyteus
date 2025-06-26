# file: autobyteus/tests/unit_tests/agent/phases/test_discoverer.py
import pytest
from unittest.mock import patch

from autobyteus.agent.phases import PhaseTransitionDiscoverer, PhaseTransitionInfo, AgentOperationalPhase

@pytest.fixture(autouse=True)
def clear_discoverer_cache():
    """Fixture to automatically clear the discoverer's cache before and after each test."""
    PhaseTransitionDiscoverer.clear_cache()
    yield
    PhaseTransitionDiscoverer.clear_cache()

def test_discovery_returns_list_of_info_objects():
    """Tests that discover() returns a non-empty list of PhaseTransitionInfo objects."""
    transitions = PhaseTransitionDiscoverer.discover()
    
    assert isinstance(transitions, list)
    assert len(transitions) > 0, "Should discover at least one transition from AgentPhaseManager"
    
    for item in transitions:
        assert isinstance(item, PhaseTransitionInfo)

def test_discovery_finds_specific_known_transition():
    """
    Tests that a specific, known transition is discovered with the correct metadata.
    We will test the 'notify_initialization_complete' transition.
    """
    transitions = PhaseTransitionDiscoverer.discover()
    
    # Find the specific transition triggered by 'notify_initialization_complete'
    init_complete_transition = next((t for t in transitions if t.triggering_method == 'notify_initialization_complete'), None)
    
    assert init_complete_transition is not None, "Transition for 'notify_initialization_complete' not found."
    
    # Verify its properties match the decorator in AgentPhaseManager
    assert init_complete_transition.source_phases == (AgentOperationalPhase.BOOTSTRAPPING,)
    assert init_complete_transition.target_phase == AgentOperationalPhase.IDLE
    assert "completes bootstrapping" in init_complete_transition.description

def test_discovery_is_cached():
    """
    Tests that the discovery process is cached after the first call by spying on inspect.getmembers.
    """
    with patch('autobyteus.agent.phases.discover.inspect.getmembers') as mock_getmembers:
        # The return value of getmembers needs to be an iterable of (name, object) tuples.
        # We can just return an empty list to prevent errors, as we only care about call count.
        mock_getmembers.return_value = []

        # First call should trigger inspect.getmembers
        PhaseTransitionDiscoverer.discover()
        mock_getmembers.assert_called_once()
        
        # Second call should use the cache and NOT trigger inspect.getmembers again
        PhaseTransitionDiscoverer.discover()
        mock_getmembers.assert_called_once() # Call count should still be 1

def test_clear_cache_works():
    """
    Tests that clear_cache() allows the discovery process to be re-run.
    """
    with patch('autobyteus.agent.phases.discover.inspect.getmembers') as mock_getmembers:
        mock_getmembers.return_value = []

        # First call - uses inspector
        PhaseTransitionDiscoverer.discover()
        assert mock_getmembers.call_count == 1
        
        # Second call - uses cache
        PhaseTransitionDiscoverer.discover()
        assert mock_getmembers.call_count == 1
        
        # Clear the cache
        PhaseTransitionDiscoverer.clear_cache()
        
        # Third call - should use inspector again
        PhaseTransitionDiscoverer.discover()
        assert mock_getmembers.call_count == 2

def test_discovered_transitions_are_sorted():
    """
    Tests that the returned list of transitions is sorted deterministically.
    """
    transitions = PhaseTransitionDiscoverer.discover()
    
    # Create a sorted version of the list based on the same key used in the implementation
    manually_sorted_transitions = sorted(transitions, key=lambda t: (t.target_phase.value, t.triggering_method))
    
    assert transitions == manually_sorted_transitions, "The discover() method should return a sorted list."
