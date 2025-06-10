import pytest
from unittest.mock import MagicMock

from autobyteus.agent.events import BaseEvent, UserMessageReceivedEvent
from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry

# A dummy handler for testing purposes
class DummyEventHandler(AgentEventHandler):
    async def handle(self, event: BaseEvent, context: MagicMock) -> None:
        pass

@pytest.fixture
def registry() -> EventHandlerRegistry:
    """Provides a clean EventHandlerRegistry instance for each test."""
    return EventHandlerRegistry()

def test_registry_initialization(registry: EventHandlerRegistry):
    """Test that the registry initializes empty."""
    assert len(registry._handlers) == 0
    assert registry.get_all_registered_event_types() == []

def test_register_handler_valid(registry: EventHandlerRegistry):
    """Test successful registration of a handler."""
    handler_instance = DummyEventHandler()
    registry.register(UserMessageReceivedEvent, handler_instance)
    
    assert registry.get_handler(UserMessageReceivedEvent) is handler_instance
    assert UserMessageReceivedEvent in registry.get_all_registered_event_types()
    assert len(registry._handlers) == 1

def test_register_handler_overwrite_raises_error(registry: EventHandlerRegistry):
    """Test that attempting to register a handler for the same event type raises a ValueError."""
    handler1 = DummyEventHandler()
    handler2 = DummyEventHandler()
    
    registry.register(UserMessageReceivedEvent, handler1)
    
    with pytest.raises(ValueError, match="Handler already registered for event class 'UserMessageReceivedEvent'"):
        registry.register(UserMessageReceivedEvent, handler2)

def test_get_handler_not_found(registry: EventHandlerRegistry):
    """Test that get_handler returns None for an unregistered event type."""
    assert registry.get_handler(UserMessageReceivedEvent) is None

def test_register_handler_invalid_event_class_type(registry: EventHandlerRegistry):
    """Test registration with an event_class that is not a type (e.g., an instance)."""
    handler_instance = DummyEventHandler()
    with pytest.raises(TypeError, match="'event_class' must be a subclass of BaseEvent"):
        # FIX: Instantiate UserMessageReceivedEvent correctly with its required argument
        # so that the type check inside registry.register() is actually reached.
        event_instance = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
        registry.register(event_instance, handler_instance) # type: ignore

def test_register_handler_invalid_event_class_inheritance(registry: EventHandlerRegistry):
    """Test registration with a class that does not inherit from BaseEvent."""
    class NotAnEvent:
        pass
    
    handler_instance = DummyEventHandler()
    with pytest.raises(TypeError, match="'event_class' must be a subclass of BaseEvent"):
        registry.register(NotAnEvent, handler_instance) # type: ignore

def test_register_handler_invalid_handler_type(registry: EventHandlerRegistry):
    """Test registration with a handler that is not an AgentEventHandler instance."""
    class NotAHandler:
        pass

    with pytest.raises(TypeError, match="'handler_instance' must be an instance of AgentEventHandler"):
        registry.register(UserMessageReceivedEvent, NotAHandler()) # type: ignore

def test_registry_repr(registry: EventHandlerRegistry):
    """Test the __repr__ method of the registry."""
    assert repr(registry) == "<EventHandlerRegistry registered_event_types=[]>"
    
    registry.register(UserMessageReceivedEvent, DummyEventHandler())
    assert repr(registry) == "<EventHandlerRegistry registered_event_types=['UserMessageReceivedEvent']>"
