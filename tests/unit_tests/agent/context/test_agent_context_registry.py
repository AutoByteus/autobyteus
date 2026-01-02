# file: autobyteus/tests/unit_tests/agent/context/test_agent_context_registry.py
import pytest
import gc
from unittest.mock import MagicMock, patch

from autobyteus.agent.context.agent_context_registry import AgentContextRegistry
from autobyteus.agent.context import AgentContext

@pytest.fixture
def clean_registry():
    """Fixture to ensure the AgentContextRegistry singleton is clean for each test."""
    instances = getattr(AgentContextRegistry, "_instances", None)
    if isinstance(instances, dict):
        instances.pop(AgentContextRegistry, None)
    
    registry = AgentContextRegistry()
    yield registry
    
    # Clean up after the test
    instances = getattr(AgentContextRegistry, "_instances", None)
    if isinstance(instances, dict):
        instances.pop(AgentContextRegistry, None)

@pytest.fixture
def mock_context() -> AgentContext:
    """Provides a mock AgentContext."""
    mock = MagicMock(spec=AgentContext)
    mock.agent_id = "test_agent_123"
    return mock

class TestAgentContextRegistry:

    def test_singleton_behavior(self, clean_registry):
        """Verify that multiple instantiations yield the same object."""
        registry1 = clean_registry
        registry2 = AgentContextRegistry()
        assert registry1 is registry2

    def test_register_and_get_context(self, clean_registry, mock_context):
        """Test basic registration and retrieval of a context."""
        clean_registry.register_context(mock_context)
        retrieved_context = clean_registry.get_context("test_agent_123")
        
        assert retrieved_context is not None
        assert retrieved_context.agent_id == "test_agent_123"
        assert retrieved_context is mock_context

    def test_get_nonexistent_context_returns_none(self, clean_registry):
        """Test that getting a context that doesn't exist returns None."""
        assert clean_registry.get_context("nonexistent_agent") is None

    def test_unregister_context(self, clean_registry, mock_context):
        """Test that a context can be unregistered."""
        clean_registry.register_context(mock_context)
        assert clean_registry.get_context("test_agent_123") is not None

        clean_registry.unregister_context("test_agent_123")
        assert clean_registry.get_context("test_agent_123") is None

    def test_unregister_nonexistent_context_is_safe(self, clean_registry):
        """Test that unregistering a non-existent context does not raise an error."""
        with patch('autobyteus.agent.context.agent_context_registry.logger') as mock_logger:
            clean_registry.unregister_context("nonexistent_agent")
            mock_logger.warning.assert_called_once() # Verify it logs the attempt

    def test_register_overwrites_existing_context(self, clean_registry, mock_context):
        """Test that registering a context with the same ID overwrites the old one."""
        mock_context_2 = MagicMock(spec=AgentContext)
        mock_context_2.agent_id = "test_agent_123"

        clean_registry.register_context(mock_context)
        assert clean_registry.get_context("test_agent_123") is mock_context

        with patch('autobyteus.agent.context.agent_context_registry.logger') as mock_logger:
            clean_registry.register_context(mock_context_2)
            mock_logger.warning.assert_called_once()

        assert clean_registry.get_context("test_agent_123") is mock_context_2

    def test_weak_reference_cleanup(self, clean_registry):
        """Verify that dead weak references are cleaned up automatically."""
        agent_id = "temp_agent_for_gc"
        
        # Create context in a limited scope
        def setup_and_register():
            temp_context = MagicMock(spec=AgentContext)
            temp_context.agent_id = agent_id
            clean_registry.register_context(temp_context)
            # At this point, the weak reference is live
            assert clean_registry.get_context(agent_id) is not None
        
        setup_and_register()
        
        # After the function, `temp_context` should be eligible for garbage collection
        gc.collect()
        
        # Getting the context again should find the dead reference and clean it up
        assert clean_registry.get_context(agent_id) is None
        # Verify the internal dictionary is also empty for that key
        assert agent_id not in clean_registry._contexts
