# file: tests/unit_tests/agent/lifecycle/test_base_processor.py
"""
Tests for BaseLifecycleProcessor.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from autobyteus.agent.lifecycle.events import LifecycleEvent
from autobyteus.agent.lifecycle.base_processor import BaseLifecycleEventProcessor


class ConcreteLifecycleProcessor(BaseLifecycleEventProcessor):
    """Concrete implementation for testing."""
    
    def __init__(self):
        self._process_called = False
        self._process_context = None
        self._process_event_data = None
    
    @property
    def event(self) -> LifecycleEvent:
        return LifecycleEvent.AGENT_READY
    
    async def process(self, context, event_data: Dict[str, Any]) -> None:
        self._process_called = True
        self._process_context = context
        self._process_event_data = event_data


class CustomOrderProcessor(BaseLifecycleEventProcessor):
    """Processor with custom order and name."""
    
    @classmethod
    def get_name(cls) -> str:
        return "custom_processor"
    
    @classmethod
    def get_order(cls) -> int:
        return 100
    
    @property
    def event(self) -> LifecycleEvent:
        return LifecycleEvent.BEFORE_LLM_CALL
    
    async def process(self, context, event_data: Dict[str, Any]) -> None:
        pass


class TestBaseLifecycleProcessor:
    """Tests for BaseLifecycleEventProcessor abstract base class."""

    def test_default_get_name_returns_class_name(self):
        """Verify default get_name returns the class name."""
        processor = ConcreteLifecycleProcessor()
        assert processor.get_name() == "ConcreteLifecycleProcessor"

    def test_default_get_order_returns_500(self):
        """Verify default get_order returns 500 (normal priority)."""
        processor = ConcreteLifecycleProcessor()
        assert processor.get_order() == 500

    def test_custom_get_name(self):
        """Verify get_name can be overridden."""
        processor = CustomOrderProcessor()
        assert processor.get_name() == "custom_processor"

    def test_custom_get_order(self):
        """Verify get_order can be overridden."""
        processor = CustomOrderProcessor()
        assert processor.get_order() == 100

    def test_event_property_returns_lifecycle_event(self):
        """Verify event property returns the correct LifecycleEvent."""
        processor = ConcreteLifecycleProcessor()
        assert processor.event == LifecycleEvent.AGENT_READY
        
        processor2 = CustomOrderProcessor()
        assert processor2.event == LifecycleEvent.BEFORE_LLM_CALL

    @pytest.mark.asyncio
    async def test_process_is_called_with_context_and_event_data(self):
        """Verify process method receives context and event_data."""
        processor = ConcreteLifecycleProcessor()
        mock_context = MagicMock()
        event_data = {"tool_name": "test_tool"}
        
        await processor.process(mock_context, event_data)
        
        assert processor._process_called is True
        assert processor._process_context is mock_context
        assert processor._process_event_data == event_data

    def test_repr_shows_event(self):
        """Verify __repr__ shows the event."""
        processor = ConcreteLifecycleProcessor()
        repr_str = repr(processor)
        assert "ConcreteLifecycleProcessor" in repr_str
        assert "agent_ready" in repr_str

    def test_abstract_methods_must_be_implemented(self):
        """Verify abstract methods raise NotImplementedError if not implemented."""
        # This should fail because abstract methods are not implemented
        with pytest.raises(TypeError):
            class IncompleteProcessor(BaseLifecycleEventProcessor):
                pass
            IncompleteProcessor()
