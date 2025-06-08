import pytest
from unittest.mock import MagicMock

from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry
from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events.agent_events import BaseEvent, UserMessageReceivedEvent, AgentReadyEvent # UPDATED: AgentStartedEvent -> AgentReadyEvent


# A dummy event handler for testing
class DummyEventHandler(AgentEventHandler):
    async def handle(self, event, context):
        pass # pragma: no cover

class AnotherDummyEventHandler(AgentEventHandler):
    async def handle(self, event, context):
        pass # pragma: no cover

# Dummy event classes
class MyCustomEvent(BaseEvent):
    pass

class NotAnEvent: # Not a subclass of BaseEvent
    pass


@pytest.fixture
def registry():
    # Ensure a fresh registry for each test if it's a singleton
    if hasattr(EventHandlerRegistry, '_instance'):
        EventHandlerRegistry._instance = None
    return EventHandlerRegistry()

def test_event_handler_registry_initialization(registry: EventHandlerRegistry):
    """Test that the registry initializes with an empty handler mapping."""
    assert not registry._handlers
    assert len(registry.get_all_registered_event_types()) == 0

def test_register_handler_success(registry: EventHandlerRegistry):
    """Test successful registration of an event handler."""
    handler_instance = DummyEventHandler()
    registry.register(UserMessageReceivedEvent, handler_instance)
    
    assert UserMessageReceivedEvent in registry._handlers
    assert registry._handlers[UserMessageReceivedEvent] is handler_instance
    assert UserMessageReceivedEvent in registry.get_all_registered_event_types()

def test_get_handler_success(registry: EventHandlerRegistry):
    """Test retrieval of a registered event handler."""
    handler_instance = DummyEventHandler()
    registry.register(UserMessageReceivedEvent, handler_instance)
    
    retrieved_handler = registry.get_handler(UserMessageReceivedEvent)
    assert retrieved_handler is handler_instance

def test_get_handler_not_found(registry: EventHandlerRegistry):
    """Test retrieval of a handler for an unregistered event class."""
    retrieved_handler = registry.get_handler(AgentReadyEvent) # UPDATED example event
    assert retrieved_handler is None

def test_register_handler_invalid_event_class_type(registry: EventHandlerRegistry):
    """Test registration with an event_class that is not a type (e.g., an instance)."""
    handler_instance = DummyEventHandler()
    with pytest.raises(TypeError, match="'event_class' must be a subclass of BaseEvent"):
        registry.register(UserMessageReceivedEvent(), handler_instance) # type: ignore

def test_register_handler_event_class_not_base_event_subclass(registry: EventHandlerRegistry):
    """Test registration with an event_class that is not a subclass of BaseEvent."""
    handler_instance = DummyEventHandler()
    with pytest.raises(TypeError, match="'event_class' must be a subclass of BaseEvent"):
        registry.register(NotAnEvent, handler_instance) # type: ignore

def test_register_handler_invalid_handler_instance_type(registry: EventHandlerRegistry):
    """Test registration with a handler_instance that is not an AgentEventHandler."""
    with pytest.raises(TypeError, match="'handler_instance' must be an instance of AgentEventHandler"):
        registry.register(UserMessageReceivedEvent, object()) # type: ignore

def test_register_handler_already_registered_error(registry: EventHandlerRegistry):
    """Test that registering a handler for an already registered event class raises ValueError."""
    handler1 = DummyEventHandler()
    handler2 = AnotherDummyEventHandler()
    
    registry.register(UserMessageReceivedEvent, handler1)
    
    with pytest.raises(ValueError, match="Handler already registered for event class 'UserMessageReceivedEvent'"):
        registry.register(UserMessageReceivedEvent, handler2)

def test_get_handler_invalid_event_class_type_arg(registry: EventHandlerRegistry):
    """Test get_handler with an invalid event_class argument type."""
    handler = registry.get_handler(UserMessageReceivedEvent()) # type: ignore
    assert handler is None 

def test_get_handler_event_class_not_base_event_subclass_arg(registry: EventHandlerRegistry):
    """Test get_handler with an event_class not subclassing BaseEvent."""
    handler = registry.get_handler(NotAnEvent) # type: ignore
    assert handler is None 

def test_get_all_registered_event_types(registry: EventHandlerRegistry):
    """Test listing all registered event types."""
    handler1 = DummyEventHandler()
    handler2 = AnotherDummyEventHandler()

    assert registry.get_all_registered_event_types() == []

    registry.register(UserMessageReceivedEvent, handler1)
    assert set(registry.get_all_registered_event_types()) == {UserMessageReceivedEvent}

    registry.register(AgentReadyEvent, handler2) # UPDATED example event
    assert set(registry.get_all_registered_event_types()) == {UserMessageReceivedEvent, AgentReadyEvent}

def test_event_handler_registry_repr(registry: EventHandlerRegistry):
    """Test the __repr__ method of the registry."""
    assert "EventHandlerRegistry" in repr(registry)
    assert "registered_event_types=[]" in repr(registry)

    registry.register(UserMessageReceivedEvent, DummyEventHandler())
    repr_str = repr(registry)
    assert "UserMessageReceivedEvent" in repr_str
    assert "EventHandlerRegistry" in repr_str
